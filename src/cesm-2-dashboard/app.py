import holoviews as hv
import geoviews as gv
import numpy as np
import panel as pn
import param
from datetime import datetime
import pandas as pd
import datetime as dt
import cftime

from dask.distributed import Client
from holoviews.operation.datashader import rasterize
from holoviews import opts
import param
from panel.viewable import Viewer

import xarray as xr
import hvplot.xarray
from pathlib import Path

gv.extension('bokeh')
hv.extension('bokeh')
pn.extension('gridstack')


DASK_SCHEDULER_ADDR = 'tcp://10.12.1.2:36391'
NWORKERS = 4

client = Client(DASK_SCHEDULER_ADDR)

client.wait_for_workers(NWORKERS)

# path where data is stored. Stored according to variable names.
parent_dir = Path('/glade/work/pdas47/cesm-annual/')
# print file names in the directory. Each file is the annual and member mean of that variable in the CESM-LENS2 dataset
files = list(parent_dir.glob('*.nc'))

print(*[f.name for f in files], sep=', ') 

ds = xr.open_mfdataset(files, parallel=True)

# convert datetimes from cftime.noleap to standard
ds = ds.convert_calendar('standard')

# rename variables as "long_name (unit)"
ds = ds.rename({k:f"{ds[k].attrs['long_name']} ({ds[k].attrs.get('units', 'unitless')})" for k in sorted(list(ds.keys()), reverse=True)})

min_year = ds.time.min().dt.year.item()
max_year = ds.time.max().dt.year.item()

variables = list(sorted(ds.keys(), reverse=True))

forcing_types = list(ds.coords['forcing_type'].values)

clim_min = ds[variables[0]].sel(time=f'2015-01-01', method='nearest').sel(forcing_type='cmip6').min()
clim_max = ds[variables[0]].sel(time=f'2015-01-01', method='nearest').sel(forcing_type='cmip6').max()

args = dict(
    ds = ds,
    min_year = min_year,
    max_year = max_year,
    variables = variables,
    forcing_types = forcing_types,
    clim_min = clim_min,
    clim_max = clim_max
)


class ClimateViewer(param.Parameterized):
    variable = param.ObjectSelector(default=variables[0], objects=variables)
    forcing_type = param.ObjectSelector(default=forcing_types[0], objects=forcing_types)
    year = param.Integer(default=2015, bounds=(min_year, max_year))   
    
    cmap = param.ObjectSelector(default='inferno', objects=['inferno', 'viridis', 'inferno_r', 'kb', 'coolwarm', 'coolwarm_r', 'Blues', 'Blues_r'])
    clim_min = param.Number(default=0)
    clim_max = param.Number(default=100)
    clim_controls_ts = param.Boolean(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_subset = None
        self.map_hv = None
        self.map_with_marker_dmap = None
        self.ts_hv = None
        self._tap_screen = ds[variables[0]].isel(time=0).sel(forcing_type='cmip6').hvplot(x='lon', y='lat', geo=True, visible=False, colorbar=False).opts(min_width=300, frame_width=800)
        self.stream = hv.streams.Tap(x=0, y=0, source=self._tap_screen)

        self._get_data()

    @param.depends('year', 'variable', 'forcing_type')
    def _get_data(self):
        self.data_subset = ds[self.variable].sel(time=f'{self.year}-01-01', method='nearest').sel(forcing_type=self.forcing_type)
        return self.data_subset

    def map_plot(self):
        var_long_name = ds[self.variable].attrs['long_name']

        if 'units' in ds[self.variable].attrs:
            clabel = f'{var_long_name} ({ds[self.variable].attrs["units"]})'
        else:
            clabel = f'{var_long_name} (undefined units)'
        
        xr_plot = self.data_subset.hvplot(
            x='lon', y='lat',
            geo=True, coastline=True,
            cmap=self.cmap, clabel=clabel, clim=(self.clim_min, self.clim_max)
        )
        
        self.map_hv = (self._tap_screen * xr_plot).opts(
            opts.Image(
                title=f"Average annual {var_long_name} on {self.year}",
                xlabel="Longitude", ylabel="Latitude",
                min_width=300, frame_width=800
            )
        )

        return self.map_hv

    @param.depends('year', 'cmap', 'forcing_type', 'variable', 'clim_min', 'clim_max')
    def map_plot_dmap(self):
        def _map_plot_dmap(x, y):
            return (self.map_plot() * hv.Scatter((x, y)).opts(color='red', marker='x', size=10, min_width=300, frame_width=800))

        self.map_with_marker_dmap = hv.DynamicMap(_map_plot_dmap, streams=[self.stream])
        return self.map_with_marker_dmap
    
    @param.depends('year', 'variable', 'forcing_type', 'clim_min', 'clim_max', 'clim_controls_ts')
    def ts_dmap(self):
        def _ts_dmap(x, y):
            if self.clim_controls_ts:
                ts_plot = ds[self.variable].sel(lat=y, lon=x%360, method='nearest').hvplot(x='time', by='forcing_type').opts(ylim=(self.clim_min, self.clim_max))
            else:
                ts_plot = ds[self.variable].sel(lat=y, lon=x%360, method='nearest').hvplot(x='time', by='forcing_type')
            return (ts_plot * hv.VLine(datetime(self.year, 1, 1))).opts(
                opts.VLine(line_dash='dashed', line_width=2, line_color='k')
            )
        
        self.ts_hv = hv.DynamicMap(_ts_dmap, streams=[self.stream])
        return self.ts_hv

viewer = ClimateViewer(name='Climate Viewer')

variable_select = pn.Param(viewer.param.variable, widgets={'variable': {'width': 250, 'width_policy': 'fit'}})
forcing_type_select = pn.Param(viewer.param.forcing_type, widgets={'forcing_type': {'width': 100, 'width_policy': 'fit'}})
cmap_select = pn.Param(viewer.param.cmap, widgets={'forcing_type': {'width': 100, 'width_policy': 'fit'}})
year_slide = pn.Param(viewer.param.year, widgets={'year': {'width': 250, 'width_policy': 'fit'}})
clim_min_inp = pn.Param(viewer.param.clim_min, widgets={'clim_min_inp': {'width': 100, 'width_policy': 'min'}})
clim_max_inp = pn.Param(viewer.param.clim_max, widgets={'clim_max_inp': {'width': 100, 'width_policy': 'min'}})
clim_ts_btn = pn.Param(viewer.param.clim_controls_ts)

dataset_controls = pn.Card(
    pn.pane.Markdown('## Dataset controls'),
    variable_select,
    year_slide,
    forcing_type_select,
    title='Dataset controls',
    sizing_mode='stretch_both'
)

plot_controls = pn.Card(
    pn.pane.Markdown('## Plot controls'),
    cmap_select,
    clim_max_inp,
    clim_min_inp, 
    clim_ts_btn,
    title='Plot controls',
    sizing_mode='stretch_both'
)

# Instantiate the template with widgets displayed in the sidebar
template = pn.template.BootstrapTemplate(
    title='CESM-2 Dashboard',
    sidebar=[dataset_controls, plot_controls],
)
# Append a layout to the main area, to demonstrate the list-like API
template.main.append(
    pn.Column(
        viewer.map_plot_dmap,
        viewer.ts_dmap,
    )
)

template.servable()

import holoviews as hv
import geoviews as gv
import panel as pn
import param
from datetime import datetime

from dask.distributed import Client
from holoviews.operation.datashader import rasterize
from holoviews import opts, streams
from panel.viewable import Viewer
import geoviews.feature as gf
import param
from cartopy import crs
from bokeh.models.formatters import PrintfTickFormatter

import xarray as xr
import hvplot.xarray
from pathlib import Path

gv.extension('bokeh')
hv.extension('bokeh')

# plot default style
opts.defaults(
    opts.Image(
        global_extent=True, projection=crs.PlateCarree(),
        aspect='equal', responsive='width'
    )
)

parent_dir = Path('/glade/work/pdas47/cesm-annual/')
files = list(parent_dir.glob('*.nc'))
print(*[f.name for f in files], sep=', ') 

ds = xr.open_mfdataset(files, parallel=True)
ds = ds.convert_calendar('standard')

# rename variables as "long_name (unit)"
ds = ds.rename({k:f"{ds[k].attrs['long_name']} ({ds[k].attrs.get('units', 'unitless')})" for k in sorted(list(ds.keys()), reverse=True)}).persist()

std_parent_dir = Path('/glade/work/pdas47/cesm-annual/std_dev/')
files = list(std_parent_dir.glob("*.nc"))

std_ds = xr.open_mfdataset(files, parallel=True)
std_ds = std_ds.convert_calendar('standard')

# rename variables similar to the annual mean dataset
std_ds = std_ds.rename({k:f"{std_ds[k].attrs['long_name']} ({std_ds[k].attrs.get('units', 'unitless')})" for k in sorted(list(std_ds.keys()), reverse=True)}).persist()

min_year = ds.time.min().dt.year.item()
max_year = ds.time.max().dt.year.item()

variables = list(sorted(ds.keys(), reverse=True))

forcing_types = list(ds.coords['forcing_type'].values)



class ColorbarControls(Viewer):
    clim = param.Range(default=(0, 100), label="Colorbar Range")
    width = param.Number(default=300)
    clim_locked = param.Boolean(default=False)

    _scientific_format_low_threshold = 0.01
    _scientific_format_high_threshold = 9999

    def __init__(self, **params):
        self._start_input = pn.widgets.FloatInput()
        self._end_input = pn.widgets.FloatInput(align='end')
        self._clim_lock = pn.widgets.Checkbox(name='Lock controls')
        super().__init__(**params)
        self._layout = pn.Column(
            pn.Row(self._start_input, self._end_input),
            self._clim_lock
        )
        self._sync_widgets()

    def __panel__(self):
        return self._layout

    @param.depends('clim', 'width', '_clim_lock.value', watch=True)
    def _sync_widgets(self):
        if self._clim_lock.value:
            self.clim_locked = True
            self._start_input.disabled = True
            self._end_input.disabled = True
        else:
            self.clim_locked = False
            self._start_input.disabled = False
            self._end_input.disabled = False

        self._start_input.name = self.name
        self._start_input.value, self._end_input.value = self.clim
        for i in [self._start_input, self._end_input]:
            i.width = int(self.width * 0.9) // 2
            i.margin = (5, 5)
            if i.value < self._scientific_format_low_threshold or i.value > self._scientific_format_high_threshold:
                i.format = PrintfTickFormatter(format="%.2e")
            else:
                i.format = '0.2f'

    @param.depends('_start_input.value', '_end_input.value', watch=True)
    def _sync_params(self):
        self.clim = (self._start_input.value, self._end_input.value)


class ClimateViewer(param.Parameterized):
    # Dataset parameters
    variable = param.ObjectSelector(default=variables[0], objects=variables)
    forcing_type = param.ObjectSelector(default=forcing_types[0], objects=forcing_types)
    year = param.Integer(default=2015, bounds=(min_year, max_year))
    
    # time-series parameters
    pointer = param.XYCoordinates((0, 0), precedence=-1)
    
    # Plotting parameters
    cmap = param.ObjectSelector(label='Colormap', default='inferno', objects=['inferno', 'viridis', 'inferno_r', 'kb', 'coolwarm', 'coolwarm_r', 'Blues', 'Blues_r'])
    cbar_controls = ColorbarControls(name='Colorbar Controls')

    # Data parameters
    data_subset = param.Parameter(default=hv.Dataset([]), precedence=-1)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # plot handles
        self.map_hv = None
        self._pointer_marker = None
        self.ts_hv = None
        self._year_marker = None
        self._cbar = None
        
        # setup stream <-> pointer connection
        self._stream = streams.Tap(x=0, y=0)
        self._stream.add_subscriber(self._update_click)
        
        # Initialize map
        self._get_map_data()
        self._plot_map()
        self._plot_pointer_marker()
        self._style_map()
        
        # Initialize Time-series
        self._get_ts_data()
        self._plot_ts()
        self._plot_year_marker()
        self._style_ts()
    
    @param.depends('variable', 'forcing_type', 'year', watch=True)
    def _get_map_data(self):
        subset = ds[self.variable].sel(time=f'{self.year}-01-01', method='nearest').sel(forcing_type=self.forcing_type).rename({'lat': 'Latitude', 'lon': 'Longitude'})
        self.data_subset = hv.Dataset(subset)

    @param.depends('data_subset', watch=True)
    def _plot_map(self):
        plot = gv.Image(
            data = self.data_subset,
            kdims = ['Longitude', 'Latitude'],
            vdims = [self.variable],
            group = 'Map',
            label = self.variable
        )
        self.map_hv = plot
        clim_range = plot.range(self.variable)
        if not self.cbar_controls.clim_locked:
            self.cbar_controls.clim = clim_range
    
    @param.depends('pointer', watch=True)
    def _plot_pointer_marker(self):
        plot = hv.Scatter(
            (self.pointer[0], self.pointer[1])
        ).opts(color='red', marker='x', size=10)
        self._pointer_marker = plot
    
    @param.depends('_plot_map', 'cmap', 'cbar_controls.clim', watch=True)
    def _style_map(self):
        styled_plot = self.map_hv.opts(
            cmap=self.cmap,
            title=f"Average {self.variable} in {self.year}",
            clim=(self.cbar_controls.clim[0], self.cbar_controls.clim[1])
        )
        self.map_hv = styled_plot
        self._update_source()
    
    def _update_source(self):
        self._stream.source = self.map_hv
    
    def _update_click(self, x, y):
        self.pointer = (x, y)
    
    @param.depends('variable', 'forcing_type', 'pointer', watch=True)
    def _get_ts_data(self):
        ts_mean_subset = ds[self.variable].sel(lat=self.pointer[1], lon=self.pointer[0]%360, method='nearest').sel(forcing_type=self.forcing_type).rename({'lat': 'Latitude', 'lon': 'Longitude'})
        self.ts_mean_subset = hv.Dataset(ts_mean_subset)
        ts_stddev_subset = std_ds[self.variable].sel(lat=self.pointer[1], lon=self.pointer[0]%360, method='nearest').sel(forcing_type=self.forcing_type).rename({'lat': 'Latitude', 'lon': 'Longitude'})
        self.ts_upper_bound = hv.Dataset(ts_mean_subset + ts_stddev_subset)
        self.ts_lower_bound = hv.Dataset(ts_mean_subset - ts_stddev_subset)
    
    @param.depends('year', watch=True)
    def _plot_year_marker(self):
        self._year_marker = hv.VLine(
            datetime(self.year, 1, 1)
        ).opts(
            line_dash = 'dashed',
            line_width = 2,
            line_color = 'grey'
        )
    
    @param.depends('pointer', 'variable', '_get_ts_data', watch=True)
    def _plot_ts(self):
        ts_mean = hv.Curve(
            data = self.ts_mean_subset,
            kdims = ['time'],
            vdims = [self.variable]
        )
        ts_bounds = hv.Area(
            data = (
                self.ts_lower_bound['time'], 
                self.ts_upper_bound[self.variable],
                self.ts_lower_bound[self.variable], 
            ),
            kdims = ['time'],
            vdims = ['upper_bound', 'lower_bound']
        )
        self.ts_hv = ts_mean * ts_bounds
    
    @param.depends('_plot_ts', watch=True)
    def _style_ts(self):
        pointer_x = f'{self.pointer[0]:.2f}°E' if self.pointer[0] >= 0 else f'{self.pointer[0]*-1:.2f}°W'
        pointer_y = f'{self.pointer[1]:.2f}°N' if self.pointer[1] >= 0 else f'{self.pointer[1]*-1:.2f}°S'
        self.ts_hv = self.ts_hv.opts(
            opts.Curve(show_legend=True, show_grid=True, responsive='width', height=300),
            opts.Area(alpha=0.3, title=f'{self.variable} at {pointer_x}, {pointer_y}'),
        )
    
    @param.depends('_plot_map', '_style_map', '_plot_pointer_marker')
    def view_map(self):
        return self.map_hv * gf.coastline * self._pointer_marker

    @param.depends('_plot_ts', '_style_ts', '_plot_year_marker')
    def view_ts(self):
        return self.ts_hv * self._year_marker
    
    def _debug(self):
        return pn.pane.HTML(self.ts_lower_bound.data)
    
    # Layout
    @property
    def template(self):
        variable_select = pn.Param(
            self.param.variable,
            widgets={'variable': {'width_policy': 'max', 'width': 100}}, 
            width_policy='fit', min_width=100, max_width=600,
            width=300, margin=(5, 5)
        )
        forcing_type_select = pn.Param(
            self.param.forcing_type, 
            widgets={'forcing_type': {'width_policy': 'max', 'width': 100}},
            width_policy='fit', min_width=100, max_width=600,
            width=300, margin=(5, 5)
        )
        year_slide = pn.Param(
            self.param.year, 
            widgets={'year': {'type': pn.widgets.IntSlider, 'width_policy': 'max', 'width': 100, 'height': 30}},
            width_policy='fit', min_width=100, max_width=600,
            width=300, margin=(5, 5)
        )

        cmap_select = pn.Param(
            self.param.cmap, 
            widgets={'cmap': {'width_policy': 'max', 'width': 100}},
            width_policy='fit', min_width=100, max_width=600,
            width=300, margin=(5, 5)
        )

        cbar_range = self.cbar_controls

        dataset_controls = pn.Card(
            variable_select,
            year_slide,
            forcing_type_select,
            title='Dataset controls',
            width_policy='fit'
        )

        plot_controls = pn.Card(
            cmap_select,
            cbar_range,
            title='Plot controls',
            width_policy='fit'
        )

        # Instantiate the template with widgets displayed in the sidebar
        template = pn.template.BootstrapTemplate(
            title='CESM-2 Dashboard',
            sidebar=[dataset_controls, plot_controls],
            main_max_width='1000px',
            sidebar_width=340
        )

        content = pn.Column(
            self.view_map,
            self.view_ts,
            align='center'
        )

        # Append a layout to the main area, to demonstrate the list-like API
        template.main.append(
            content
        )

        return template
    
climate_viewer = ClimateViewer()

template = climate_viewer.template
template.servable()
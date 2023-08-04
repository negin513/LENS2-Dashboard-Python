# SIParCS - Interactivite visualization of climate data

This repository hosts notebooks and code written to visualize the [CESM-LENS2](https://www.cesm.ucar.edu/community-projects/lens2) dataset.

## Getting started

1. Clone the repository:

`git clone https://github.com/negin513/LENS2-Dashboard-Python.git`

2. Navigate to project directory:

`cd LENS2-Dashboard-Python`

3. Create conda environment:

`conda create --prefix ./.env --file environment.yml`


4. Start a jupyterlab session and run the notebooks. Start jupyterlab session:

`jupyter lab`


## Serve the app

1. Start a dask scheduler

`dask scheduler --host localhost --port 8786`

2. Start dask workers - 2 workers, with 2GB memory each

`dask worker --host localhost --nworkers 2 --memory-limit '2GB' localhost:8786`

3. Start panel server

`panel serve src/cesm-2-dashboard/app.py --allow-websocket-origin="*" --autoreload`

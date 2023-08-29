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

## Using Docker Locally with seperate containers for dask
***Note:*** Make sure app.py has `CLUSTER_TYPE = 'scheduler:8786'` set before building the container image. 
The commands used will pull from the ncote Docker Hub repository if you do not build locally.
You can specify your own docker image names to replace anything that begins with `ncote/`

1. Build the docker images for the web application and dask

`docker build -t ncote/lens2-docker .`

`docker build -f Dockerfile.dask -t ncote/dask-lens2 .`

2. Create a docker network to run the containers on

`docker network create dask`

3. Start the Dask schedulers and workers
***Note:*** This can be run in individual terminal windows or by running the container in detached mode with the `-d` flag

`docker run --network dask -p 8787:8787 --name scheduler ncote/dask-lens2 dask-scheduler`

`docker run --network dask ncote/dask-lens2 dask-worker scheduler:8786`

4. Start the Web Application

`docker run --network dask -p 5006:5006 ncote/lens2-docker`

# Interactive LENS-2 Dashboard

This repository hosts notebooks and code written to visualize the [CESM-LENS2](https://www.cesm.ucar.edu/community-projects/lens2) dataset.

| GitHub Action | Status |
| --- | --- |
| LENS2 CICD Pipeline |  ![Build](https://github.com/NicholasCote/LENS2-Dashboard-Python/actions/workflows/cicd-workflow.yaml/badge.svg) |

## Running Locally

### Getting started

1. Clone the repository:

`git clone https://github.com/negin513/LENS2-Dashboard-Python.git`

2. Navigate to project directory:

`cd LENS2-Dashboard-Python`

3. Create conda environment:

`conda env create --file environment.yml -n lens2`
or 
`mamba env create --file environment.yml -n lens2`

4. activate the environment:

`conda activate lens2`


## Exploring via notebook: 

5. Start a jupyterlab session and run the notebooks. Start jupyterlab session:

`jupyter lab`

## Serve the app from outside notebook:

After creating and activating the environment:

1. In one terminal, start a dask scheduler

`dask scheduler --host localhost --port 8786 &`

2. Start dask workers - 2 workers, with 2GB memory each

`dask worker --host localhost --nworkers 2 --memory-limit '2GB' localhost:8786 &`

3. Start panel server

`panel serve src/cesm-2-dashboard/app.py --allow-websocket-origin="*" --autoreload`

### Using Docker Locally with separate containers for Dask
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

`docker run -e ENV_NAME=lens2 --network dask -p 5006:5006 ncote/lens2-docker`

## Running on Kubernetes (K8s)
### Push image to Container Registry

In order to deploy your container build on K8s it needs to be located in a container registry that the cluster has access to. The NFS NCAR Cloud has a Container Registry onsite that can be used for image hosting to speed up new image pulls. For this example we will use Docker Hub as it's publicly available and accessible to the NSF NCAR Cluster.

1. Tag your image with a descriptive tag, `:latest` should not be used

`docker tag ncote/lens2-docker:latest ncote/lens2-docker:2023-12-8`

`docker tag ncote/dask-lens2:latest ncote/dask-lens2:v1`

The first image name is the local container. The second image name is the new tag to be push. 
*** Note: By default Docker Hub is used. `ncote` is my Docker Hub repository name. A custom container registry can be utilized by providing the repository URL, the repository name, and the image name and tag.

2. Push the image

`docker push ncote/lens2-docker:2023-12-8`

`docker push ncote/dask-lens2:v1`

The images are now in Docker Hub and can be used in our Helm chart. 

### Update Helm chart
There is a directory named lens2-helm that contains a Helm chart to deploy this application on K8s. 

#### values.yaml
You can use and edit the values.yaml file to configure the Deployment for your environment. The 
values.yaml file in this repository is configured to deploy to the NSF NCAR K8s cluster with information specific to me. Here is a list of values to update for a unique configuration:

  * `name:` & `group` : I set these to be the same value, a descriptive name for the application. 
  * `condaEnv:` is the name of the conda environment to activate on launch
  * `tls:`
    - `fqdn:` is the unique URL used for the deployment. The NSF NCAR K8s cluster utilizes External DNS to create resolvable addresses in the `.k8s.ucar.edu` domain only.
    - `secretName:` is a K8s secret that stores the TLS certificate for your application. This needs to be unique for your FQDN. `cert-manager` will create a valid certificate for you if one does not already exist for your FQDN. `secretName:` should be utilized if you were to have multiple deployments for the same FQDN but different paths. In our example we deploy the main app and the Dask scheduler in the same file. You could technically split these up in to 2 different helm charts. Both would use the same `secretName:` as long as the `fqdn:` value was the same.
  * `webapp:`
    - `container:`
      - `image:` the image to use for the web application. This is the image name and tag we pushed for the LENS2 application above.
  * `scheduler:`
    - `container:`
      - `image:` the image to use for the Dask cluster. This is the image name and tag we pushed for the Dask cluster above.

The rest of the values are applicable to any Deployment but can be customized if needed.

#### Chart.yaml

The `Chart.yaml` file doesn't have as many important configuration details but it should be updated when you update your application. There are 2 lines specifically to address, `version:` and `appVersion:`. You can use whatever versioning scheme you prefer, the example uses Semantic Versioning that you would update accordingly for each new deployment.

### Deploy Helm Chart
#### NSF NCAR CD

The NSF NCAR Cloud has a Continuous Deployment tool that can be configured to automatically update your application when changes are made to the Helm chart in your GitHub repository. An administrator would need to configure this for you details can be found at this [link to Argo Instructions](https://ncar.github.io/cisl-cloud/how-to/K8s/argocd/argo-user.html)

#### Helm install

The Helm chart used has values that utilize cert-manager, External DNS, and Nginx Ingress Controller to manage host records, certificates, and proxying the application to a valid HTTPS URL. Helm install can be used to deploy to a K8s cluster that utilizes a similar architecture. 

`helm install app-chart-name ./lens2-helm`

Data: https://drive.google.com/file/d/1GF5UiAb7QJ5eeNh7p4Y2EzXVh10A6Bbt/view?usp=drive_link


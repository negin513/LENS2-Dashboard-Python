# Use an official Python runtime as a base image
FROM docker.io/mambaorg/micromamba:latest

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
#RUN pip install --no-cache-dir -r requirements.txt

# Copy the environment.yml file to the container
#COPY environment.yml .
#RUN mamba env create -f environment.yml --force

# Copy the current directory contents into the container at /usr/src/app
COPY src/cesm-2-dashboard/ environment.yml .

# Install any needed packages specified in requirements.yml
RUN micromamba env create -f environment.yml

# Activate the environment by providing ENV_NAME as an environment variable at runtime 
# Make port bokeh application port to the world outside this container
EXPOSE 5006

CMD ["panel", "serve", "app.py", "--allow-websocket-origin=ncote-lens2-demo.k8s.ucar.edu", "--autoreload"]

#panel serve src/cesm-2-dashboard/app.py --cluster_type LocalCluster --allow-websocket-origin="*"

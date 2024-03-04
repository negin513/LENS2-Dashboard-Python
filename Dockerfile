# Use an official Python runtime as a base image
FROM docker.io/mambaorg/micromamba:latest

# Set the working directory in the container to /app
WORKDIR /home/mambauser/app

# Copy the current directory contents into the container at /usr/src/app
COPY src/cesm-2-dashboard/ environment.yml .

# Install any needed packages specified in requirements.yml
RUN micromamba env create -f environment.yml

RUN chown -R mambauser:mambauser /home/mambauser/app

# Activate the environment by providing ENV_NAME as an environment variable at runtime 
# Make port bokeh application port to the world outside this container
EXPOSE 5006

USER mambauser

CMD ["panel", "serve", "app.py", "--allow-websocket-origin=ncote-lens2-demo.k8s.ucar.edu", "--autoreload"]
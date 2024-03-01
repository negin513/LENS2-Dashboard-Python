# Use an official Python runtime as a base image
FROM python:3.8-slim

RUN apk update && apk add python3-dev \
    gcc \
    libc-dev

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
COPY src/cesm-2-dashboard/ requirements.txt .

# Install any needed packages specified in requirements.yml
RUN pip install --no-cache-dir -r requirements.txt 


# Activate the environment. This ensures that the environment is activated each time a new container is started from the image.
#RUN echo "source activate $(head -1 /tmp/environment.yml | cut -d' ' -f2)" > ~/.bashrc

# Activate the conda environment
#RUN ["conda", "run", "-n", "lens2", "python", "--version"]

# Make port bokeh application port to the world outside this container
EXPOSE 5006

CMD ["panel", "serve", "app.py", "--allow-websocket-origin=*", "--autoreload"]

#panel serve src/cesm-2-dashboard/app.py --cluster_type LocalCluster --allow-websocket-origin="*"

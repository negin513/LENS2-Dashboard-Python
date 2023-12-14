import os
import boto3
from botocore import UNSIGNED
from botocore.config import Config

# This requests package is imported to disable certificate access warnings. 
# SSL certificates can be provided and this would not be required.
import requests.packages.urllib3
# We aren't verifying certs to start so this line is disable warnings
requests.packages.urllib3.disable_warnings()

# This file is used to download data files required for the dashboard

# Define the Stratus S3 client to be used in other operations
def stratus_s3_client():
    # Define the API endpoint for stratus
    endpoint = "https://stratus.ucar.edu/"
    # Create a boto3 sessions
    session = boto3.session.Session()
    # Create the S3 client based on the variables we set and provided
    s3_client = session.client(
        service_name='s3', 
        endpoint_url=endpoint, 
        config=Config(signature_version=UNSIGNED),
        verify=False)
    # Return the client so that it can be used in other functions
    return s3_client

# Define the Stratus S3 resource to be used in other operations    
def stratus_s3_resource():
    # Define the API endpoint for stratus
    endpoint = "https://stratus.ucar.edu/"
    # Create a boto3 sessions
    session = boto3.session.Session()
    # Create the S3 resource based on the variables we set and provided
    s3_resource = session.resource(
        service_name='s3', 
        endpoint_url=endpoint, 
        config=Config(signature_version=UNSIGNED),
        verify=False)
    # Return the client so that it can be used in other functions
    return s3_resource

# Define a function to list all the objects stored in a bucket
def list_bucket_objs(bucket):
    bucket_objs = []
    # Use the S3 resource already defined to make the call
    s3_resource = stratus_s3_resource()
    # Get the individual bucket resources for the bucket name provided in the function 
    bucket = s3_resource.Bucket(bucket)
    # Iterate through the response to show all objects contained within the bucket
    for obj in bucket.objects.all():
        #print(obj.key)
        bucket_objs.append(obj.key)
    return bucket_objs

# Define a function to download a file/object to a bucket
def download_file(filename, bucketname):
    # Use the S3 client already defined to make the call
    s3_client = stratus_s3_client()
    if "/" in filename:
        directory_split = filename.split("/")
        print(directory_split)
        directory_split.pop(len(directory_split)-1)
        print(directory_split)
        directory = "/".join(directory_split)
        if os.path.exists(directory):
            # Open a local file with the same filename as the one we are downloading
            s3_client.download_file(bucketname, filename, filename)
        else:
            print(directory)
            os.makedirs(directory, exist_ok=True)
            s3_client.download_file(bucketname, filename, filename)
    else:
            s3_client.download_file(bucketname, filename, filename)

def get_data_files():
    bucket_objs = list_bucket_objs('cisl-cloud-users')
    for objs in bucket_objs:
        if 'LENS2-ncote-dashboard/data_files' in objs:
            if '.tar.gz' in objs:
                pass
            else:
                print('Downloading ' + objs)
                download_file(objs,'cisl-cloud-users')
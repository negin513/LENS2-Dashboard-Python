from dask_jobqueue import PBSCluster
from dask.distributed import Client
import sys

cluster = PBSCluster(
    job_name = 'climate-viewer',
    cores = 1,
    memory = '4GiB',
    processes = 4,
    local_directory = '/glade/work/pdas47/scratch/pbs.$PBS_JOBID/dask/spill',
    resource_spec = 'select=1:ncpus=1:mem=4GB',
    queue = 'casper',
    walltime = '00:30:00',
    interface = 'ib0',
    worker_extra_args = ["--lifetime", "25m", "--lifetime-stagger", "4m"]
)

print(cluster)

cluster.scale(32)
client = Client(cluster)
client.wait_for_workers(32)

print(cluster.dashboard_link)

input("Press any key to exit..")

cluster.close()
sys.exit(0)
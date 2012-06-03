from celery.task import task
from celery.task.sets import TaskSet

from djeuscan.models import Package

from djeuscan.management.commands.regen_rrds import regen_rrds
from djeuscan.management.commands.update_counters import update_counters
from djeuscan.management.commands.scan_metadata import ScanMetadata
from djeuscan.management.commands.scan_portage import ScanPortage, \
    purge_versions as scan_portage_purge
from djeuscan.management.commands.scan_upstream import ScanUpstream, \
    purge_versions as scan_upstream_purge


@task
def regen_rrds_task():
    regen_rrds()


@task
def update_counters_task():
    update_counters()


@task
def scan_metadata_task(query, obj=None):
    logger = scan_metadata_task.get_logger()
    logger.info("Starting metadata scanning for package %s ...", query)

    scan_metadata = ScanMetadata()
    scan_metadata.scan(query, obj)


@task
def scan_metadata_all_task():
    job = TaskSet(tasks=[
        scan_metadata_task.subtask(('%s/%s' % (pkg.category, pkg.name), pkg))
        for pkg in Package.objects.all()
    ])
    job.apply_async()


@task
def scan_portage_all_task(purge=False):
    logger = scan_portage_all_task.get_logger()
    logger.info("Starting Portage scanning...")

    scan_portage = ScanPortage()
    scan_portage.scan()

    if purge:
        logger.info("Purging")
        scan_portage_purge()


@task
def scan_portage_task(query, purge=False):
    logger = scan_portage_task.get_logger()
    logger.info("Starting Portage package scanning: %s ...", query)

    scan_portage = ScanPortage()
    scan_portage.scan(query)

    if purge:
        logger.info("Purging")
        scan_portage_purge()


@task
def scan_portage_purge_task():
    scan_portage_purge()


@task
def scan_upstream_all_task(purge=False):
    tasks = [scan_upstream_task.subtask(('%s/%s' % (pkg.category, pkg.name), ))
             for pkg in Package.objects.all()]

    if purge:
        tasks.append(scan_upstream_purge_task.subtask())

    job = TaskSet(tasks=tasks)
    job.apply_async()


@task
def scan_upstream_task(query):
    logger = scan_upstream_task.get_logger()
    logger.info("Starting upstream scanning for package %s ...", query)

    scan_upstream = ScanUpstream()
    scan_upstream.scan(query)


@task
def scan_upstream_purge_task():
    scan_upstream_purge()


launchable_tasks = [
    regen_rrds_task,
    update_counters_task,
    scan_metadata_task,
    scan_metadata_all_task,
    scan_portage_all_task,
    scan_portage_task,
    scan_portage_purge_task,
    scan_upstream_all_task,
    scan_upstream_task,
    scan_upstream_purge_task,
]

import logging
import traceback

from docleaner.api.core.job import JobStatus
from docleaner.api.services.repository import Repository

logger = logging.getLogger(__name__)


async def process_job_in_sandbox(jid: str, repo: Repository) -> None:
    """Executes the job identified by jid in a sandbox, post-processes the resulting metadata
    and updates the job within the repository according to the result."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"No job with ID {jid} found")
    if job.status != JobStatus.QUEUED:
        raise ValueError(
            f"Can't execute job {jid}, because it's not in QUEUED state (state is {job.status})"
        )
    await repo.update_job(jid, status=JobStatus.RUNNING)
    logger.debug(
        "Processing job %s (%s) in %s",
        jid,
        job.type.id,
        type(job.type.sandbox).__name__,
    )
    try:
        result = await job.type.sandbox.process(job.src)
    except Exception:
        logger.warning(f"Exception in sandbox.process():\n{traceback.format_exc()}")
        await repo.add_to_job_log(jid, "Error during sandbox processing")
        await repo.update_job(
            jid=jid,
            status=JobStatus.ERROR,
            result=None,
            metadata_result=None,
            metadata_src=None,
        )
        return
    logger.debug("Job %s has been processed", jid)
    for logline in result.log:
        await repo.add_to_job_log(jid, logline)
    try:
        metadata_result = job.type.metadata_processor(result.metadata_result)
        metadata_src = job.type.metadata_processor(result.metadata_src)
        await repo.update_job(
            jid=jid,
            status=JobStatus.SUCCESS if result.success else JobStatus.ERROR,
            result=result.result,
            metadata_result=metadata_result,
            metadata_src=metadata_src,
        )
    except Exception:
        logger.warning(
            f"Exception during metadata post-processing:\n{traceback.format_exc()}"
        )
        await repo.add_to_job_log(jid, "Error during metadata post-processing")
        await repo.update_job(
            jid=jid,
            status=JobStatus.ERROR,
            result=None,
            metadata_result=None,
            metadata_src=None,
        )

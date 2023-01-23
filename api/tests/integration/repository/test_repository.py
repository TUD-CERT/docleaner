from docleaner.api.core.job import Job, JobType
from docleaner.api.services.repository import Repository


async def test_store_large_documents(repo: Repository) -> None:
    """Storing and retrieving documents larger than 16 MB, which is the MongoDB BSON
    document size limit. Ensure that the repository implements a workaround to save large documents."""
    large_document = b"X" * 1024 * 1024 * 20  # 20 MB payload
    jid = await repo.add_job(large_document, "large.pdf", JobType.PDF)
    await repo.update_job(jid, result=large_document)
    job = await repo.find_job(jid)
    assert isinstance(job, Job)
    assert job.src == job.result == large_document

from docleaner.api.core.job import JobStatus


def status_to_string(status: JobStatus) -> str:
    return JobStatus(status).name

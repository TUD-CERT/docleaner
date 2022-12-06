import abc

from docleaner.api.core.job import Job


class JobQueue(abc.ABC):
    """Interface for an asynchronous task processor. Enqueued jobs are expected to be
    performed and their status flag updated eventually."""

    async def enqueue(self, job: Job) -> None:
        """Adds a job to the processing queue to later be picked up by a worker.
        A job is only accepted if it carries an ID and is in CREATED state."""
        raise NotImplementedError()

    async def wait_for(self, job: Job) -> None:
        """Waits until the given job either completed successfully or was aborted due to an error."""
        raise NotImplementedError()

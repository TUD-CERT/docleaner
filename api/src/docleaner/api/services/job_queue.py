import abc

from docleaner.api.core.job import Job


class JobQueue(abc.ABC):
    """Interface for an asynchronous task processor. Enqueued jobs are expected to be
    performed and their status flag updated eventually."""

    @abc.abstractmethod
    async def enqueue(self, job: Job) -> None:
        """Adds a job to the processing queue to later be picked up by a worker.
        A job is only accepted if it carries an ID and is in CREATED state."""
        raise NotImplementedError()

    async def shutdown(self) -> None:
        """Instructs the job queue to perform any required shutdown work
        such as cancelling or waiting for remaining tasks."""
        pass

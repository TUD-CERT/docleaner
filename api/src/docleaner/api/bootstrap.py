from configparser import ConfigParser
import importlib
import logging
import os
from typing import List, Optional, Tuple

from docleaner.api.adapters.clock.system_clock import SystemClock
from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.async_job_queue import AsyncJobQueue
from docleaner.api.adapters.repository.mongodb_repository import MongoDBRepository
from docleaner.api.core.job import JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


def bootstrap(
    config: ConfigParser,
    log_level: str = "info",
    clock: Optional[Clock] = None,
    file_identifier: Optional[FileIdentifier] = None,
    queue: Optional[JobQueue] = None,
    repo: Optional[Repository] = None,
) -> Tuple[Clock, FileIdentifier, List[JobType], JobQueue, Repository]:
    """Initializes and returns plugins, adapters and service components."""
    # Initialize logging
    numeric_log_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError(f"Invalid log level {log_level}")
    logging.basicConfig(level=numeric_log_level)
    logger = logging.getLogger(__name__)
    logger.info(
        "Bootstrapping docleaner r%s", importlib.metadata.version("docleaner-api")
    )
    logger.info("Log level: %s", log_level)
    # Load configured plugins
    job_types = []
    for section in config.sections():
        if section.startswith("plugins."):
            logger.info("Initializing %s", section)
            plugin = importlib.import_module(f"docleaner.api.{section}")
            job_types.extend(plugin.get_job_types(config))
    logger.info("Registered job types: %s", ", ".join([j.id for j in job_types]))
    # Initialize adapters
    if clock is None:
        clock = SystemClock()
    if file_identifier is None:
        file_identifier = MagicFileIdentifier()
    if repo is None:
        repo = MongoDBRepository(clock, job_types, "database", 27017)
    if queue is None:
        available_cpu_cores = len(os.sched_getaffinity(0))
        queue = AsyncJobQueue(repo, available_cpu_cores)
    return clock, file_identifier, job_types, queue, repo

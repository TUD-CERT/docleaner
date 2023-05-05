"""CLI Management utility to receive status updates or run maintenance tasks.
Requires an out-of-process database instance such as MongoDB.
Maintenance tasks are intended to be run via a periodic scheduling tool such as cron."""
import argparse
import asyncio
from configparser import ConfigParser
from datetime import timedelta
import os
import sys
from typing import Optional

from docleaner.api.bootstrap import bootstrap
from docleaner.api.core.job import JobStatus
from docleaner.api.entrypoints.ctl.utils import status_to_string
from docleaner.api.services.jobs import (
    get_job,
    get_job_src,
    get_job_stats,
    get_jobs,
    purge_jobs,
)
from docleaner.api.services.sessions import purge_sessions


async def purge(
    config: ConfigParser,
    no_standalone_job_purging: bool,
    no_session_purging: bool,
    job_keepalive: int,
    session_keepalive: int,
    quiet: bool = False,
) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap(
        config, log_level="warning"
    )
    if not no_standalone_job_purging:
        purged_jids = await purge_jobs(
            purge_after=timedelta(minutes=job_keepalive), repo=repo
        )
        if len(purged_jids) > 0 and not quiet:
            print(f"Purged standalone jobs: {len(purged_jids)}")
    if not no_session_purging:
        purged_sids = await purge_sessions(
            purge_after=timedelta(minutes=session_keepalive), repo=repo
        )
        if len(purged_sids) > 0 and not quiet:
            print(f"Purged sessions: {len(purged_sids)}")


async def show_status(
    config: ConfigParser,
) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap(
        config, log_level="warning"
    )
    total_jobs, created, queued, running, success, error = await get_job_stats(repo)
    current_jobs = created + queued + running + success + error
    print(
        f"{current_jobs} jobs in db (C: {created} | Q: {queued} | R: {running} |"
        f" S: {success} | E: {error}), {total_jobs} total"
    )


async def diag_list(config: ConfigParser, status: JobStatus) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap(
        config, log_level="warning"
    )
    jobs = await get_jobs(status, repo)
    print("jid / type")
    for jid, job_type, job_log in jobs:
        print(f"{jid} / {job_type}")


async def diag_job_details(
    config: ConfigParser, jid: str, src_out_path: Optional[str] = None
) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap(
        config, log_level="warning"
    )
    try:
        job_status, job_type, job_log, _, _, sid = await get_job(jid, repo)
        if job_status in [JobStatus.QUEUED, JobStatus.SUCCESS]:
            # Prevent inspection of queued and successful jobs
            # that shouldn't require diagnosis (privacy)
            raise ValueError(
                f"Inspection of jid {jid} not possible due to its job status {job_status}"
            )
        print(f"jid:    {jid}")
        print(f"status: {status_to_string(job_status)}")
        print(f"sid:    {sid}")
        print("--- sandbox log ---")
        for log in job_log:
            print(log)
        if src_out_path is not None:
            job_src, job_name = await get_job_src(jid, repo)
            with open(src_out_path, "wb") as f:
                f.write(job_src)
            print(
                f"Source document written to {src_out_path}, original name was {job_name}"
            )
    except ValueError as e:
        print(e)
        sys.exit(1)


async def debug_delete_job(config: ConfigParser, jid: str) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap(
        config, log_level="warning"
    )
    try:
        await repo.delete_job(jid)
        print(f"Job {jid} deleted successfully from the database")
    except ValueError as e:
        print(e)
        sys.exit(1)


def cmd_tasks(args: argparse.Namespace, config: ConfigParser) -> None:
    asyncio.run(
        purge(
            config,
            args.no_standalone_job_purging,
            args.no_session_purging,
            args.job_keepalive,
            args.session_keepalive,
            args.quiet,
        )
    )


def cmd_status(args: argparse.Namespace, config: ConfigParser) -> None:
    asyncio.run(show_status(config))


def cmd_diag_err(args: argparse.Namespace, config: ConfigParser) -> None:
    if args.jid is not None:
        asyncio.run(diag_job_details(config, args.jid, args.save_src))
    else:
        asyncio.run(diag_list(config, JobStatus.ERROR))


def cmd_diag_run(args: argparse.Namespace, config: ConfigParser) -> None:
    if args.jid is not None:
        asyncio.run(diag_job_details(args.jid, args.save_src))
    else:
        asyncio.run(diag_list(config, JobStatus.RUNNING))


def cmd_debug(args: argparse.Namespace, config: ConfigParser) -> None:
    if args.delete_jid is not None:
        asyncio.run(debug_delete_job(config, args.delete_jid))
    else:
        print("No debug command specified")


def init() -> ConfigParser:
    if "DOCLEANER_CONF" not in os.environ:
        raise ValueError("Environment variable DOCLEANER_CONF is not set!")
    _config = ConfigParser()
    _config.read(os.environ["DOCLEANER_CONF"])
    return _config


def main() -> None:
    parser = argparse.ArgumentParser(description="docleaner management utility")
    subparsers = parser.add_subparsers(help="command")
    tasks_parser = subparsers.add_parser(
        "tasks", help="Run management tasks (jobs/session purging)"
    )
    tasks_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress output of deleted jobs and sessions",
    )
    tasks_parser.add_argument(
        "-j",
        "--job-keepalive",
        type=int,
        default=10,
        help="Delete standalone jobs after X minutes (default: 10 minutes)",
    )
    tasks_parser.add_argument(
        "-s",
        "--session-keepalive",
        type=int,
        default=60 * 24,
        help="Delete sessions after X minutes (default: 24 hours)",
    )
    tasks_parser.add_argument(
        "--no-session-purging",
        action="store_true",
        help="Do not purge jobs associated with a session",
    )
    tasks_parser.add_argument(
        "--no-standalone-job-purging",
        action="store_true",
        help="Do not purge standalone jobs",
    )
    tasks_parser.set_defaults(func=cmd_tasks)
    status_parser = subparsers.add_parser(
        "status", help="Show job counters (current and total)"
    )
    status_parser.set_defaults(func=cmd_status)
    diag_err_parser = subparsers.add_parser(
        "diag-err",
        help="Diagnose job errors. By default, lists jobs that ended in an erroneous state.",
    )
    diag_err_parser.add_argument(
        "-j", "--jid", type=str, help="Show details for a specific job"
    )
    diag_err_parser.add_argument(
        "--save-src",
        type=str,
        help="Write a job's source document to the given path (only with -j)",
    )
    diag_err_parser.set_defaults(func=cmd_diag_err)
    diag_run_parser = subparsers.add_parser(
        "diag-run",
        help="Diagnose running jobs. By default, lists currently running jobs.",
    )
    diag_run_parser.add_argument(
        "-j", "--jid", type=str, help="Show details for a specific job"
    )
    diag_run_parser.add_argument(
        "--save-src",
        type=str,
        help="Write a job's source document to the given path (only with -j)",
    )
    diag_run_parser.set_defaults(func=cmd_diag_run)
    debug_parser = subparsers.add_parser(
        "debug",
        help="Debug utilities operating directly on the database. USE WITH CAUTION, does not enforce data consistency!",
    )
    debug_parser.add_argument(
        "-d", "--delete-jid", type=str, help="Deletes a job via its jid"
    )
    debug_parser.set_defaults(func=cmd_debug)
    args = parser.parse_args()
    if "func" in args:
        args.func(args, init())
    else:
        print("No command specified")


if __name__ == "__main__":
    main()

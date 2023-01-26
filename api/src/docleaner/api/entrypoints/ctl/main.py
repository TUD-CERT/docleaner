"""CLI Management utility to receive status updates or run maintenance tasks.
Requires an out-of-process database instance such as MongoDB.
Maintenance tasks are intended to be run via a periodic scheduling tool such as cron."""
import argparse
import asyncio
from datetime import timedelta

from docleaner.api.bootstrap import bootstrap
from docleaner.api.services.jobs import get_job_stats, purge_jobs
from docleaner.api.services.sessions import purge_sessions


async def purge(
    no_standalone_job_purging: bool,
    no_session_purging: bool,
    job_keepalive: int,
    session_keepalive: int,
    quiet: bool = False,
) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap()
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


async def status() -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap()
    total_jobs, created, queued, running, success, error = await get_job_stats(repo)
    current_jobs = created + queued + running + success + error
    print(
        f"{current_jobs} jobs in db (C: {created} | Q: {queued} | R: {running} | S: {success} | E: {error}), {total_jobs} total"
    )


def cmd_tasks(args: argparse.Namespace) -> None:
    asyncio.run(
        purge(
            args.no_standalone_job_purging,
            args.no_session_purging,
            args.job_keepalive,
            args.session_keepalive,
            args.quiet,
        )
    )


def cmd_status(args: argparse.Namespace) -> None:
    asyncio.run(status())


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
    status_parser = subparsers.add_parser("status", help="Show current job status")
    status_parser.set_defaults(func=cmd_status)
    args = parser.parse_args()
    if "func" in args:
        args.func(args)
    else:
        print("No command specified")


if __name__ == "__main__":
    main()

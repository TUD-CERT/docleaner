"""Utility to run maintenance tasks (such puring stale jobs and sessions),
intended to be run via a periodic scheduling tool such as cron."""
import argparse
import asyncio
from datetime import timedelta

from docleaner.api.bootstrap import bootstrap
from docleaner.api.services.jobs import purge_jobs
from docleaner.api.services.sessions import purge_sessions


async def purge(
    no_standalone_job_purging: bool,
    no_session_purging: bool,
    job_keepalive: int,
    session_keepalive: int,
) -> None:
    clock, file_identifier, job_types, queue, repo = bootstrap()
    if not no_standalone_job_purging:
        purged_jids = await purge_jobs(
            purge_after=timedelta(minutes=job_keepalive), repo=repo
        )
        if len(purged_jids) > 0:
            print(f"Purged standalone jobs: {len(purged_jids)}")
    if not no_session_purging:
        purged_sids = await purge_sessions(
            purge_after=timedelta(minutes=session_keepalive), repo=repo
        )
        if len(purged_sids) > 0:
            print(f"Purged sessions: {len(purged_sids)}")


def main():
    parser = argparse.ArgumentParser(description="docleaner maintenance utility")
    parser.add_argument(
        "-j",
        "--job-keepalive",
        type=int,
        default=10,
        help="Delete standalone jobs after X minutes (default: 10 minutes)",
    )
    parser.add_argument(
        "-s",
        "--session-keepalive",
        type=int,
        default=60 * 24,
        help="Delete sessions after X minutes (default: 24 hours)",
    )
    parser.add_argument(
        "--no-session-purging",
        action="store_true",
        help="Do not purge jobs associated with a session",
    )
    parser.add_argument(
        "--no-standalone-job-purging",
        action="store_true",
        help="Do not purge standalone jobs",
    )
    args = parser.parse_args()
    asyncio.run(
        purge(
            args.no_standalone_job_purging,
            args.no_session_purging,
            args.job_keepalive,
            args.session_keepalive,
        )
    )


if __name__ == "__main__":
    main()

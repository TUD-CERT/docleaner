#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
from typing import List, Tuple


def build_compose_cmdline(config: str) -> List[str]:
    """Returns a subprocess-ready docker-compose command line."""
    docker_compose_file = os.path.join('deployment/docker', f'{config}.yml')
    if not os.path.isfile(docker_compose_file):
        raise ValueError(f'The file {docker_compose_file} does not exist')
    return ['docker-compose', '-p', 'docleaner', '-f', docker_compose_file]


def compose(command: List[str], config: str = 'development'):
    """Executes the given command via docker-compose and attaches to the project's output."""
    cmdline = build_compose_cmdline(config) + command
    p = subprocess.Popen(cmdline)
    try:
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


def test():
    """Initializes the test environment, checks typing and runs all tests."""
    # Launch test environment
    config = 'development'
    compose_cmd = build_compose_cmdline(config) + ['up', '-d']
    subprocess.call(compose_cmd)
    # Check coding style
    stylecheck_cmd = build_compose_cmdline(config) + ['exec', 'api', 'check_style']
    subprocess.call(stylecheck_cmd)
    # Check types
    typecheck_cmd = build_compose_cmdline(config) + ['exec', 'api', 'check_types']
    subprocess.call(typecheck_cmd)
    # Perform tests
    test_cmd = build_compose_cmdline(config) + ['exec', 'api', 'pytest', '-svv']
    subprocess.call(test_cmd)
    # Environment shutdown
    down_cmd = build_compose_cmdline(config) + ['down', '-v', '--rmi', 'local']
    subprocess.call(down_cmd)


def parse_args() -> Tuple[argparse.Namespace, List[str]]:
    """Parses and returns command line arguments."""
    parser = argparse.ArgumentParser(description='Project build and management script')
    subparsers = parser.add_subparsers(required=True, dest='subcmd', title='subcmd')

    compose_parser = subparsers.add_parser('compose', help='Command passthrough to docker-compose', )
    compose_parser.add_argument('cmd', help='Compose command line')

    subparsers.add_parser('test', help='Run test suite')

    return parser.parse_known_args()


if __name__ == '__main__':
    args, remainder = parse_args()

    if args.subcmd == 'compose':
        compose([args.cmd] + remainder)
    elif args.subcmd == 'test':
        test()

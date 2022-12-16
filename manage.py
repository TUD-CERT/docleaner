#!/usr/bin/env python3
import argparse
import json
import os
import signal
import subprocess
import tempfile
import time
from threading import Thread
from typing import List, Optional, Tuple

dev_env_process: Optional[subprocess.Popen] = None


def build_compose_cmdline(config: str) -> List[str]:
    """Returns a subprocess-ready docker-compose command line."""
    docker_compose_file = os.path.join("deployment/docker", f"{config}.yml")
    if not os.path.isfile(docker_compose_file):
        raise ValueError(f"The file {docker_compose_file} does not exist")
    return ["docker-compose", "-p", "docleaner", "-f", docker_compose_file]


def wait_for_service(service: str, config: str = "development") -> None:
    """Blocks until the named service's container is running."""
    waiting = True
    while waiting:
        status = json.loads(subprocess.check_output(build_compose_cmdline(config) + ["ps", "--format", "json"]))
        for s in status:
            if s["Service"] == service and s["State"] == "running":
                waiting = False
                break
        time.sleep(0.2)


def run(podman_socket: str, config: str = "development") -> None:
    """Launches a dev environment via docker-compose and optionally attaches to the collective container output."""
    global dev_env_process
    cmdline = build_compose_cmdline(config) + ["up"]
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as runtime_tmp:
        dummy_socket = podman_proc = None
        if podman_socket == "none":
            dummy_socket = tempfile.NamedTemporaryFile()
            podman_socket = dummy_socket.name
        elif podman_socket == "auto":
            print('Launching podman service')
            podman_socket = f"{runtime_tmp}/podman.sock"
            podman_proc = subprocess.Popen(["podman", "system", "service", "-t", "0", f"unix://{podman_socket}"])
        env["DOCLEANER_PODMAN_SOCKET"] = podman_socket
        dev_env_process = subprocess.Popen(cmdline, env=env)
        try:
            dev_env_process.wait()
        except KeyboardInterrupt:
            dev_env_process.send_signal(signal.SIGINT)
            dev_env_process.wait()
        finally:
            if dummy_socket is not None:
                dummy_socket.close()
            if podman_proc is not None:
                print('Terminating podman service')
                podman_proc.terminate()
                podman_proc.wait()


def shell(service: str, config: str = "development") -> None:
    """Launches a shell within a container of the given (service) name."""
    cmdline = build_compose_cmdline(config) + ["exec", service, "/bin/sh"]
    p = subprocess.Popen(cmdline)
    try:
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


def shutdown(config: str = "development") -> None:
    """Stops the environment and attempts to remove ephemeral containers and images."""
    stop_cmd = build_compose_cmdline(config) + ["down", "--rmi", "local"]
    subprocess.run(stop_cmd)


def test(podman_socket: str) -> None:
    """Initializes the test environment, checks typing and runs all tests."""
    global dev_env_process
    # Launch test environment
    print("Launching test environment")
    config = "development"
    t = Thread(target=run, args=[podman_socket, config])
    t.start()
    wait_for_service("api")
    print("Checking coding style")
    stylecheck_cmd = build_compose_cmdline(config) + ["exec", "api", "check_style"]
    subprocess.call(stylecheck_cmd)
    print("Checking types")
    typecheck_cmd = build_compose_cmdline(config) + ["exec", "api", "check_types"]
    subprocess.call(typecheck_cmd)
    print("Performing tests")
    test_cmd = build_compose_cmdline(config) + ["exec", "api", "pytest", "-svv"]
    subprocess.call(test_cmd)
    # Environment shutdown
    if dev_env_process is not None:
        dev_env_process.send_signal(signal.SIGINT)
        dev_env_process.wait()
    shutdown(config)


def parse_args() -> Tuple[argparse.Namespace, List[str]]:
    """Parses and returns command line arguments."""
    parser = argparse.ArgumentParser(description="Project build and management script")
    subparsers = parser.add_subparsers(required=True, dest="subcmd", title="subcmd")

    run_parser = subparsers.add_parser("run", help="Launches a development environment via docker-compose")
    run_parser.add_argument("--podman-socket", type=str, default="auto",
                            help="podman socket path to bind into containers, 'auto' "
                                 "to launch the podman service or 'none' to disable podman")

    shell_parser = subparsers.add_parser("shell", help="Provides a shell for a specific service")
    shell_parser.add_argument("service", help="Service name")

    subparsers.add_parser("shutdown", help="Stops development environment and removes runtime fragments")
    test_parser = subparsers.add_parser("test", help="Run test suite")
    test_parser.add_argument("--podman-socket", type=str, default="auto",
                             help="podman socket path to bind into containers, 'auto' "
                                  "to launch the podman service or 'none' to disable podman")

    return parser.parse_known_args()


if __name__ == "__main__":
    args, remainder = parse_args()

    if args.subcmd == "run":
        run(podman_socket=args.podman_socket)
    elif args.subcmd == "shell":
        shell(service=args.service)
    elif args.subcmd == "shutdown":
        shutdown()
    elif args.subcmd == "test":
        test(podman_socket=args.podman_socket)

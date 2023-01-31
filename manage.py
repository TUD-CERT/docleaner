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


def build_compose_cmdline(config: str, project: str = "docleaner") -> List[str]:
    """Returns a subprocess-ready docker-compose command line."""
    docker_compose_file = os.path.join("deployment/docker", f"{config}.yml")
    if not os.path.isfile(docker_compose_file):
        raise ValueError(f"The file {docker_compose_file} does not exist")
    return ["docker-compose", "-p", project, "-f", docker_compose_file]


def wait_for_service(service: str, logline: str, config: str = "development", project: str = "docleaner") -> None:
    """Blocks until the named service's container is running."""
    waiting = True
    while waiting:
        # Wait for container to start
        status = json.loads(subprocess.check_output(build_compose_cmdline(config, project) + ["ps", "--format", "json"]))
        for s in status:
            if s["Service"] == service and s["State"] == "running":
                waiting = False
        time.sleep(0.2)
    start_time = int(time.time())
    while True:
        # Wait until logline appears in container's output
        time.sleep(0.2)
        service_log = subprocess.check_output(build_compose_cmdline(config, project) + ["logs", "--no-log-prefix", "--tail", "1", "--since", str(start_time), service])
        if logline.encode("utf-8") in service_log:
            break


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
    wait_for_service("api", "Development environment is ready")
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


def build() -> None:
    config = "development"
    proj = "docleaner-build"
    os.makedirs("dist", exist_ok=True)
    print("Launching build environment")
    env = os.environ.copy()
    env["DOCLEANER_PODMAN_SOCKET"] = "/tmp"  # Has to be set, but isn't required to build
    subprocess.run(build_compose_cmdline(config, proj) + ["up", "-d", "api"], env=env)
    wait_for_service("api", "Development environment is ready", project=proj)
    print("Building docleaner-api wheel")
    subprocess.run(build_compose_cmdline(config, proj) + ["exec", "api", "npm", "run", "build-prod"], env=env)
    subprocess.run(build_compose_cmdline(config, proj) + ["exec", "api", "python3", "setup.py", "bdist_wheel"], env=env)
    api_version = subprocess.check_output(build_compose_cmdline(config, proj) + [
        "exec",
        "api",
        "python3",
        "-c",
        "from importlib.metadata import version; print(version('docleaner-api'))"], env=env).decode("utf-8").strip()
    subprocess.run(build_compose_cmdline(config, proj) + ["cp", f"api:/srv/dist/docleaner_api-{api_version}-py3-none-any.whl", "dist/"], env=env)
    print("Building docleaner-api container image")
    subprocess.run(["docker", "build", "-f", "deployment/docker/Dockerfile.api", "-t", f"docleaner/api:{api_version}", "."])
    subprocess.run(["docker", "save", "-o", f"dist/docleaner_api-{api_version}.tar", f"docleaner/api:{api_version}"])
    subprocess.run(["docker", "rmi", f"docleaner/api:{api_version}"])
    print("Removing build environment")
    subprocess.run(build_compose_cmdline(config, proj) + ["down"], env=env)
    subprocess.run(build_compose_cmdline(config, proj) + ["rm"], env=env)


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
    test_parser = subparsers.add_parser("test", help="Runs the test suite")
    test_parser.add_argument("--podman-socket", type=str, default="auto",
                             help="podman socket path to bind into containers, 'auto' "
                                  "to launch the podman service or 'none' to disable podman")

    subparsers.add_parser("build", help="Assembles the project into distributable components (to dist/)")

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
    elif args.subcmd == "build":
        build()

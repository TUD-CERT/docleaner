#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from threading import Thread
from typing import List, Optional, Tuple

dev_env_process: Optional[subprocess.Popen] = None


def build_compose_cmdline(config: str, project: str = "docleaner") -> List[str]:
    """Returns a subprocess-ready podman-compose command line."""
    podman_compose_file = os.path.join("deployment/podman", f"{config}.yml")
    if not os.path.isfile(podman_compose_file):
        raise ValueError(f"The file {podman_compose_file} does not exist")
    return ["podman-compose", "-p", project, "-f", podman_compose_file]


def wait_for_service(service: str, logline: str, project: str = "docleaner") -> str:
    """Blocks until the named compose project's container is running and its stdout contains logline.
    Returns the service ID."""
    # Wait for container to start
    while len(service_data := json.loads(subprocess.check_output(["podman", "ps",
                                                                  "--filter", f"label=io.podman.compose.project={project}",
                                                                  "--filter", f"label=com.docker.compose.service={service}",
                                                                  "--filter", "status=running",
                                                                  "--format", "json"],
                                                                 stderr=subprocess.STDOUT).decode("utf-8"))) == 0:
        time.sleep(0.2)
    service_id = service_data.pop()["Id"]
    start_time = int(time.time())
    # Wait until logline appears in container's output
    while logline not in subprocess.check_output(["podman", "logs",
                                                  "--since", str(start_time),
                                                  "--tail", "1",
                                                  service_id],
                                                 stderr=subprocess.STDOUT).decode("utf-8"):
        time.sleep(0.5)
    return service_id


def run(podman_socket: str, config: str = "development") -> None:
    """Launches a dev environment via podman-compose and attaches to the container's output."""
    global dev_env_process
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as runtime_tmp:
        dummy_socket = podman_proc = None
        if podman_socket == "none":
            # Bind a dummy file as socket into the dev environment
            dummy_socket = tempfile.NamedTemporaryFile()
            podman_socket = dummy_socket.name
        elif podman_socket == "auto":
            print('[*] Launching podman service')
            podman_socket = f"{runtime_tmp}/podman.sock"
            podman_proc = subprocess.Popen(["podman", "system", "service", "-t", "0", f"unix://{podman_socket}"])
        env["DOCLEANER_PODMAN_SOCKET"] = podman_socket
        cmdline = build_compose_cmdline(config) + ["up"]
        dev_env_process = subprocess.Popen(cmdline, env=env)
        try:
            dev_env_process.wait()
        except KeyboardInterrupt:
            shutdown()
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
    stop_cmd = build_compose_cmdline(config) + ["down"]
    subprocess.run(stop_cmd)


def test(podman_socket: str) -> None:
    """Initializes the test environment, checks typing and runs all tests."""
    global dev_env_process
    # Launch test environment
    print("[*] Launching test environment")
    t = Thread(target=run, args=[podman_socket])
    t.start()
    service_id = wait_for_service("api", "Development environment is ready")
    print("[*] Checking coding style")
    subprocess.check_call(["podman", "exec", service_id, "check_style"])
    print("[*] Checking types")
    subprocess.check_call(["podman", "exec", service_id, "check_types"])
    print("[*] Performing tests")
    subprocess.check_call(["podman", "exec", service_id, "pytest", "-svv"])
    # Environment shutdown
    if dev_env_process is not None:
        dev_env_process.send_signal(signal.SIGINT)
        dev_env_process.wait()
    shutdown()


def build(include_nested: bool, theme: str) -> None:
    config = "development"
    proj = "docleaner-build"
    shutil.rmtree("dist", ignore_errors=True)
    os.makedirs("dist/plugins", exist_ok=True)
    print("[*] Launching build environment")
    env = os.environ.copy()
    env["DOCLEANER_PODMAN_SOCKET"] = "/tmp"  # Has to be set, but isn't required for build
    subprocess.check_call(build_compose_cmdline(config, proj) + ["up", "-d", "api"], env=env)
    service_id = wait_for_service("api", "Development environment is ready", project=proj)
    print(f"[*] Building docleaner-api wheel with {theme} theme")
    subprocess.check_call(["podman", "exec", service_id, "select_theme", theme])
    subprocess.check_call(["podman", "exec", service_id, "npm", "run", "build-prod"])
    subprocess.check_call(["podman", "exec", service_id, "python3", "setup.py", "bdist_wheel"])
    api_version = subprocess.check_output(["podman", "exec", service_id, "python3", "-c",
                                           "from importlib.metadata import version; print(version('docleaner-api'))"])\
        .decode("utf-8").strip()
    subprocess.check_call(["podman", "cp", f"{service_id}:/srv/dist/docleaner_api-{api_version}-py3-none-any.whl", "dist/"])
    print("[*] Shutting down build environment")
    subprocess.check_call(build_compose_cmdline(config, proj) + ["down"])
    subprocess.check_call(["podman", "rmi", "localhost/docleaner-build_api:latest"])
    # Build plugins
    for dirpath, _, filenames in os.walk("api/src/docleaner/api/plugins"):
        if "Containerfile" in filenames:
            subprocess.check_call(["api/scripts/build_plugin", os.path.join(dirpath, "Containerfile"), "dist/plugins"])
    print("Building docleaner/api container image")
    subprocess.check_call(["podman", "build", "-f", "deployment/podman/Containerfile.api",
                           "-t", f"docleaner/api:{api_version}-{theme}",
                           "--build-arg", f"INCLUDE_PLUGINS={str(include_nested).lower()}",
                           "."])
    subprocess.check_call(["podman", "save", "-o", f"dist/docleaner_api-{api_version}-{theme}.tar", f"docleaner/api:{api_version}-{theme}"])
    subprocess.check_call(["podman", "rmi", f"docleaner/api:{api_version}-{theme}"])
    # Create default configuration files
    shutil.copyfile("deployment/podman/docleaner.conf", "dist/docleaner.conf")
    shutil.copyfile("deployment/podman/nginx.dev.conf", "dist/nginx.insecure.conf")
    shutil.copyfile("deployment/podman/nginx.tls.conf", "dist/nginx.tls.conf")
    with open("deployment/podman/production.yml", "r") as src, open("dist/docker-compose.yml", "w") as dst:
        dst.write(src.read().replace("$REVISION", f"{api_version}-{theme}"))


def parse_args() -> Tuple[argparse.Namespace, List[str]]:
    """Parses and returns command line arguments."""
    parser = argparse.ArgumentParser(description="Project build and management script")
    subparsers = parser.add_subparsers(required=True, dest="subcmd", title="subcmd")

    run_parser = subparsers.add_parser("run", help="Launches a development environment via podman-compose")
    run_parser.add_argument("-s", "--podman-socket", type=str, default="none",
                            help="Host podman socket path to bind into containers, 'auto' "
                                 "to launch a usermode podman service on startup "
                                 "or 'none' to disable and use nested containers")

    shell_parser = subparsers.add_parser("shell", help="Provides a shell for a specific service")
    shell_parser.add_argument("service", help="Service name")

    subparsers.add_parser("shutdown", help="Stops development environment and removes runtime fragments")
    test_parser = subparsers.add_parser("test", help="Runs the test suite")
    test_parser.add_argument("-s", "--podman-socket", type=str, default="none",
                             help="Host podman socket path to bind into containers, 'auto' "
                                  "to launch a usermode podman service on startup "
                                  "or 'none' to disable and use nested containers")

    build_parser = subparsers.add_parser("build", help="Assembles the project into distributable components (to dist/)")
    build_parser.add_argument("-n", "--nested", action="store_true", help="Include nested containerized plugin images")
    build_parser.add_argument("-t", "--theme", type=str, default="default", help="Build with selected web frontend theme")
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
        build(include_nested=args.nested, theme=args.theme)

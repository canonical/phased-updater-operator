# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.

"""Functions for managing and interacting with the workload.

The intention is that this module could be used outside the context of a charm.
"""

import logging
import shutil
from pathlib import Path
from subprocess import CalledProcessError, check_output

from charmlibs import apt

from charms.operator_libs_linux.v1.systemd import service_restart, service_running

logger = logging.getLogger(__name__)

BACKEND_PACKAGES = [
    "python3-simplejson",
    "python3-debian",
    "python3-keyring",
    "python3-lazr.restfulclient",
    "python3-launchpadlib",
]

FRONTEND_PACKAGES = [
    "nginx"
]

PACKAGES = BACKEND_PACKAGES + FRONTEND_PACKAGES

APP_DIR = Path("/app")
APP = Path("/app/phased-updater")


def install() -> None:
    """Install the script, crontab, and frontend"""
    _install_packages()
    _install_app()
    _install_crontab()

def _install_crontab():
    shutil.copy(source_path / "crontab", Path("/etc/cron.d") / "phased-updater")

def _install_app():
    source_path = Path(__file__).parent.parent / "app"
    APP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, APP_DIR, dirs_exist_ok=True)

def _install_packages():
    try:
        apt.update()
    except CalledProcessError as e:
        logger.error(f"failed to update package cache: {e}")
        raise

    for package in PACKAGES:
        try:
            apt.add_package(package)
        except apt.PackageNotFoundError:
            logger.error(f"Failed to find package {package} in package cache")
            raise
        except apt.PackageError as e:
            logger.error(f"Failed to install {package}: {e}")
            raise

def start() -> None:
    # Nothing to start
    pass

def get_version() -> str | None:
    """Get the running version of the workload."""
    version = check_output([APP, "--version"]).decode("utf-8")
    return version

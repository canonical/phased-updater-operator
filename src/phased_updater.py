# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.

"""Functions for managing and interacting with the workload.

The intention is that this module could be used outside the context of a charm.
"""

import logging
import shutil
from pathlib import Path
from subprocess import CalledProcessError

from charmlibs import apt

logger = logging.getLogger(__name__)

PACKAGES = [
    "python3-simplejson",
    "python3-debian",
    "python3-keyring",
    "python3-lazr.restfulclient",
    "python3-launchpadlib",
]

APP_DIR = Path("/app")


def install() -> None:
    """Install the workload (by installing a snap, for example)."""
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

    # install the actual script and the module(s) it imports locally
    source_path = Path(__file__).parent.parent / "app"
    APP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, APP_DIR, dirs_exist_ok=True)

    # install the crontab
    shutil.copy(source_path / "crontab", Path("/etc/cron.d") / "phased-updater")


def start() -> None:
    """Start the workload (by running a commamd, for example)."""
    # You'll need to implement this function.
    # Ideally, this function should only return once the workload is ready to use.


# Functions for interacting with the workload, for example over HTTP:


def get_version() -> str | None:
    """Get the running version of the workload."""
    # You'll need to implement this function (or remove it if not needed).
    return None

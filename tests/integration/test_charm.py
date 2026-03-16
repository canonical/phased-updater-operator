# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
import pytest

import requests
import time

from phased_updater import NGINX_SITE_CONFIG_PATH

logger = logging.getLogger(__name__)

APP = "phased-updater-operator"

def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test."""
    juju.deploy(charm.resolve(), app=APP)
    juju.wait(jubilant.all_active)


def test_nginx_is_up(juju: jubilant.Juju):
    """Test that nginx is up and serving content."""
    # Get the IP address of the unit
    unit = juju.status().apps[APP].units[f"{APP}/0"]
    ip_address = unit.public_address

    # Make an HTTP request to the nginx server
    url = f"http://{ip_address}:8080"
    count = 0
    status_code = None
    while count < 10:
        try:
            status_code = requests.get(url).status_code
            break
        except requests.exceptions.ConnectionError:
            logger.info("Nginx is not up yet, retrying...")
            count += 1
            time.sleep(1)
            continue

    # There won't be an index page yet, so this wil 404, but we want to make
    # sure nginx is up and responding
    assert status_code == 404

    # check if the virtual host is there
    juju.ssh(f"{APP}/0", f"ls -l {NGINX_SITE_CONFIG_PATH}")
    juju.ssh(f"{APP}/0", f"grep /var/www/phased-updater {NGINX_SITE_CONFIG_PATH}")

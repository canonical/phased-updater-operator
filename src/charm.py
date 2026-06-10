#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the application."""

import logging

import ops
from charms.traefik_k8s.v2.ingress import (
    IngressPerAppReadyEvent,
    IngressPerAppRequirer,
    IngressPerAppRevokedEvent,
)

import phased_updater

logger = logging.getLogger(__name__)

PORT = 80  # must match the nginx config (TODO)
CONFIG_FILE = phased_updater.APP_DIR / "config"
CONFIG_TEMPLATE = """\
# Configuration file for run-phased-updater
# run-phased-updater will source this file and construct the command-line
# for phased-updater.

# Send out an email to uploaders if an update is stopped due to errors
SEND_EMAIL={send_email}

# Run without changing any phasing
DRY_RUN={dry_run}

# List of ubuntu releases to ignore, comma-separated.
# Example: focal,jammy
IGNORE_RELEASES={ignore_releases}
"""


class PhasedUpdaterOperatorCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        self.ingress = IngressPerAppRequirer(
            self, port=PORT, strip_prefix=True, relation_name="ingress"
        )

        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.config_changed, self._on_config_changed)
        framework.observe(self.on.secret_changed, self._on_secret_changed)

        # there isn't really anything to configure here for ingress
        framework.observe(self.ingress.on.ready, self._on_ingress_ready)
        framework.observe(self.ingress.on.revoked, self._on_ingress_revoked)

    def _on_ingress_ready(self, event: IngressPerAppReadyEvent):
        logger.info("This app's ingress URL: %s", event.url)

    def _on_ingress_revoked(self, event: IngressPerAppRevokedEvent):
        logger.info("This app no longer has ingress")

    def _on_install(self, event: ops.InstallEvent):
        """Install the workload on the machine."""
        self.unit.status = ops.MaintenanceStatus("Setting up environment")
        try:
            phased_updater.install()
        except Exception:
            self.unit.status = ops.BlockedStatus(
                "Failed to setup the environment. Check 'juju debug-log' for details."
            )
        self.unit.status = ops.ActiveStatus()

    def _on_secret_changed(self, event: ops.SecretChangedEvent):
        """Handle secret changes."""
        self.unit.status = ops.MaintenanceStatus("Updating secret")
        self.update_secrets()
        self.unit.status = ops.ActiveStatus()

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle config changes."""
        self.update_secrets()
        self.update_config()
        phased_updater.restart()

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.MaintenanceStatus("starting workload")
        phased_updater.restart()
        version = phased_updater.get_version()
        if version is not None:
            self.unit.set_workload_version(version)
        self.unit.set_ports(PORT)
        self.unit.status = ops.ActiveStatus()

    def update_config(self):
        """Update configuration file from charm config."""
        logging.info("Updating configuration")
        send_email = self.config["send_email"]
        dry_run = self.config["dry_run"]
        # XXX assert the format of ignore_releases is correct (comma-separated list of releases)
        ignore_releases = self.config["ignore_releases"]
        with open(CONFIG_FILE, "w") as config_file:
            config_file.write(
                CONFIG_TEMPLATE.format(
                    send_email=send_email,
                    dry_run=dry_run,
                    ignore_releases=ignore_releases,
                )
            )

    def update_secrets(self):
        """Update secrets."""
        logging.info("Updating secrets")
        try:
            launchpadlib_secret_id = str(self.config["launchpadlib_secret_id"])
        except KeyError:
            logger.error("Missing 'launchpadlib_secret_id' in charm config.")
            self.unit.status = ops.BlockedStatus(
                "Missing 'launchpadlib_secret_id' in charm config. Please set "
                "it and run 'juju config'."
            )
            return

        try:
            launchpadlib_secret = self.model.get_secret(id=launchpadlib_secret_id)
        except (ops.SecretNotFoundError, ops.model.ModelError, TypeError):
            logger.error(f"No 'launchpadlib_secret_id' secret named {launchpadlib_secret_id}.")
            self.unit.status = ops.BlockedStatus(f"Missing {launchpadlib_secret_id} secret.")
            return

        launchpadlib_credentials = launchpadlib_secret.get_content(refresh=True).get("credentials")
        if not launchpadlib_credentials:
            logger.error("Launchpadlib credentials not found")
            self.unit.status = ops.BlockedStatus("Missing launchpadlib credentials")
            return

        phased_updater.store_launchpadlib_credentials(launchpadlib_credentials)


if __name__ == "__main__":  # pragma: nocover
    ops.main(PhasedUpdaterOperatorCharm)

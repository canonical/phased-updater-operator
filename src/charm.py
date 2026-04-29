#!/usr/bin/env python3
# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.

"""Charm the application."""

import logging

import ops

import phased_updater

logger = logging.getLogger(__name__)


class PhasedUpdaterOperatorCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.start, self._on_start)
        framework.observe(self.on.config_changed, self._on_config_changed)

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

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle config changes."""
        self.update_secrets()
        phased_updater.restart()

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.MaintenanceStatus("starting workload")
        phased_updater.restart()
        version = phased_updater.get_version()
        if version is not None:
            self.unit.set_workload_version(version)
        self.unit.status = ops.ActiveStatus()

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

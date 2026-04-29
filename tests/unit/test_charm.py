# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import pytest
from ops import testing

from charm import PhasedUpdaterOperatorCharm


class MockPhasedUpdater:
    def __init__(
        self,
        version="1.0.0",
        installed=False,
        running=False,
        config={},
        launchpadlib_credentials={},
    ):
        self.version = version
        self.installed = installed
        self.running = running
        self.config = config
        self.launchpadlib_credentials = launchpadlib_credentials
        self.restart_called = False

    def install(self):
        """Simulate the installation process."""
        self.installed = True

    def is_installed(self):
        return self.installed

    def is_running(self):
        """Simulate checking if the service is running."""
        return self.running

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def restart(self):
        self.stop()
        self.start()
        self.restart_called = True

    def store_launchpadlib_credentials(self, launchpadlib_credentials):
        self.launchpadlib_credentials = launchpadlib_credentials

    def get_version(self):
        return self.version


def test_install(monkeypatch: pytest.MonkeyPatch):
    phasedupdater = MockPhasedUpdater()
    monkeypatch.setattr("charm.phased_updater", phasedupdater)
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    state_in = testing.State()
    state_out = ctx.run(ctx.on.install(), state_in)
    assert state_out.unit_status == testing.ActiveStatus()
    assert phasedupdater.is_installed()


@pytest.fixture
def phasedupdater_installed(monkeypatch: pytest.MonkeyPatch):
    phasedupdater = MockPhasedUpdater(installed=True)
    monkeypatch.setattr("charm.phased_updater", phasedupdater)
    return phasedupdater


def test_start(phasedupdater_installed: MockPhasedUpdater):
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    state_out = ctx.run(ctx.on.start(), testing.State())
    assert state_out.unit_status == testing.ActiveStatus()
    assert state_out.workload_version == phasedupdater_installed.get_version()
    assert phasedupdater_installed.is_running()


def test_config_changed(phasedupdater_installed: MockPhasedUpdater):
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    test_credentials = {"credentials": "mysecret"}
    secret = testing.Secret(tracked_content=test_credentials)
    state_in = testing.State(config={"launchpadlib_secret_id": secret.id}, secrets=[secret])
    _ = ctx.run(ctx.on.config_changed(), state_in)
    assert phasedupdater_installed.launchpadlib_credentials == test_credentials["credentials"]
    assert phasedupdater_installed.restart_called


def test_missing_config(phasedupdater_installed: MockPhasedUpdater):
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    state_in = testing.State()
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert phasedupdater_installed.launchpadlib_credentials == {}
    # restart is still called
    assert phasedupdater_installed.restart_called
    assert state_out.unit_status == testing.BlockedStatus(
        "Missing 'launchpadlib_secret_id' in charm config. Please set it and run 'juju config'."
    )


def test_missing_secret(phasedupdater_installed: MockPhasedUpdater):
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    test_credentials = {"credentials": "mysecret"}
    secret = testing.Secret(tracked_content=test_credentials)
    # Provide a valid secret ID, but the secret is not included in the state
    state_in = testing.State(config={"launchpadlib_secret_id": secret.id})
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert phasedupdater_installed.launchpadlib_credentials == {}
    # restart is still called
    assert phasedupdater_installed.restart_called
    assert state_out.unit_status == testing.BlockedStatus(f"Missing {secret.id} secret.")


def test_invalid_secret_content(phasedupdater_installed: MockPhasedUpdater):
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    # Create a secret with invalid content (not a dict with 'credentials' key)
    invalid_credentials = {"invalid_key": "value"}
    invalid_secret = testing.Secret(tracked_content=invalid_credentials)
    state_in = testing.State(
        config={"launchpadlib_secret_id": invalid_secret.id}, secrets=[invalid_secret]
    )
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert phasedupdater_installed.launchpadlib_credentials == {}
    # restart is still called
    assert phasedupdater_installed.restart_called
    assert state_out.unit_status == testing.BlockedStatus("Missing launchpadlib credentials")

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

from pathlib import Path as RealPath

import pytest
from ops import testing

import phased_updater
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
def phasedupdater_installed(monkeypatch: pytest.MonkeyPatch, tmp_path):
    phasedupdater = MockPhasedUpdater(installed=True)
    monkeypatch.setattr("charm.phased_updater", phasedupdater)
    monkeypatch.setattr("charm.CONFIG_FILE", tmp_path / "config")
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


def test_secret_changed(phasedupdater_installed: MockPhasedUpdater):
    """Test that secret_changed updates credentials, ends active, and does NOT restart."""
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    test_credentials = {"credentials": "anothersecret"}
    secret = testing.Secret(tracked_content=test_credentials)
    state_in = testing.State(config={"launchpadlib_secret_id": secret.id}, secrets=[secret])
    state_out = ctx.run(ctx.on.secret_changed(secret=secret), state_in)
    assert phasedupdater_installed.launchpadlib_credentials == test_credentials["credentials"]
    assert state_out.unit_status == testing.ActiveStatus()


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


@pytest.mark.parametrize(
    "send_email,dry_run,ignore_releases",
    [
        (True, False, ""),
        (True, True, ""),
        (False, False, ""),
        (False, True, ""),
        (True, False, "focal"),
        (True, False, "focal,jammy"),
        (False, True, "focal,jammy,questing"),
    ],
)
def test_update_config(
    phasedupdater_installed: MockPhasedUpdater,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    send_email: bool,
    dry_run: bool,
    ignore_releases: str,
):
    """Test update_config() writes the correct values to the config file."""
    monkeypatch.setattr(PhasedUpdaterOperatorCharm, "update_secrets", lambda self: None)
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    config = {
        "send_email": send_email,
        "dry_run": dry_run,
        "ignore_releases": ignore_releases,
    }
    ctx.run(ctx.on.config_changed(), testing.State(config=config))
    config_file = tmp_path / "config"
    assert config_file.exists()
    content = config_file.read_text()
    assert f"SEND_EMAIL={send_email}\n" in content
    assert f"DRY_RUN={dry_run}\n" in content
    assert f"IGNORE_RELEASES={ignore_releases}\n" in content


@pytest.fixture
def crontab_path(monkeypatch, tmp_path):
    """Redirect phased_updater.Path("/etc/cron.d") to tmp_path."""

    def fake_path(p):
        if str(p) == "/etc/cron.d":
            return tmp_path
        return RealPath(p)

    monkeypatch.setattr(phased_updater, "Path", fake_path)
    return tmp_path / "phased-updater"


def test_crontab_http_proxy_only(monkeypatch, crontab_path):
    monkeypatch.setenv("JUJU_CHARM_HTTP_PROXY", "http://proxy.example.com:3128")
    monkeypatch.delenv("JUJU_CHARM_HTTPS_PROXY", raising=False)

    phased_updater._install_crontab()

    content = crontab_path.read_text()
    assert "http_proxy=http://proxy.example.com:3128" in content
    assert phased_updater.NO_HTTPS_PROXY in content


def test_crontab_https_proxy_only(monkeypatch, crontab_path):
    monkeypatch.delenv("JUJU_CHARM_HTTP_PROXY", raising=False)
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "https://proxy.example.com:3128")

    phased_updater._install_crontab()

    content = crontab_path.read_text()
    assert "https_proxy=https://proxy.example.com:3128" in content
    assert phased_updater.NO_HTTP_PROXY in content


def test_crontab_both_proxies(monkeypatch, crontab_path):
    monkeypatch.setenv("JUJU_CHARM_HTTP_PROXY", "http://proxy.example.com:3128")
    monkeypatch.setenv("JUJU_CHARM_HTTPS_PROXY", "https://proxy.example.com:3128")

    phased_updater._install_crontab()

    content = crontab_path.read_text()
    assert "http_proxy=http://proxy.example.com:3128" in content
    assert "https_proxy=https://proxy.example.com:3128" in content


def test_crontab_no_proxies(monkeypatch, crontab_path):
    monkeypatch.delenv("JUJU_CHARM_HTTP_PROXY", raising=False)
    monkeypatch.delenv("JUJU_CHARM_HTTPS_PROXY", raising=False)

    phased_updater._install_crontab()

    content = crontab_path.read_text()
    assert phased_updater.NO_HTTP_PROXY in content
    assert phased_updater.NO_HTTPS_PROXY in content

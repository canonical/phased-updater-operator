# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import pytest
from ops import testing

from charm import PhasedUpdaterOperatorCharm

class MockPhasedUpdater:

    def __init__(self, version="1.0.0", installed=False, running=False):
        self.version = version
        self.installed = installed
        self.running = running

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

    def get_version(self):
        return self.version


def mock_get_version():
    """Get a mock version string without executing the workload code."""
    return "1.0.0"


def test_install(monkeypatch: pytest.MonkeyPatch):
    phasedupdater = MockPhasedUpdater()
    monkeypatch.setattr("charm.phased_updater", phasedupdater)
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    state_in = testing.State()
    state_out = ctx.run(ctx.on.install(), state_in)
    assert state_out.unit_status == testing.ActiveStatus()
    assert phasedupdater.is_installed()

def test_start(monkeypatch: pytest.MonkeyPatch):
    phasedupdater = MockPhasedUpdater(installed=True)
    monkeypatch.setattr("charm.phased_updater", phasedupdater)
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    state_out = ctx.run(ctx.on.start(), testing.State())
    assert state_out.unit_status == testing.ActiveStatus()
    assert phasedupdater.is_running()

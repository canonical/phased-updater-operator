# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import pytest
from ops import testing

from charm import PhasedUpdaterOperatorCharm

class MockPhasedUpdater:

    def __init__(self):
        self.version = "1.0.0"
        self.installed = False

    def install(self):
        """Simulate the installation process."""
        self.installed = True

    def is_installed(self):
        return self.installed


def mock_get_version():
    """Get a mock version string without executing the workload code."""
    return "1.0.0"


def test_install(monkeypatch: pytest.MonkeyPatch):
    phasedupdater = MockPhasedUpdater()
    monkeypatch.setattr("charm.phased_updater", phasedupdater)
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    state_in = testing.State()
    state_out = ctx.run(ctx.on.install(), state_in)
    assert state_out.unit_status == testing.MaintenanceStatus("Setting up environment")
    assert phasedupdater.is_installed()

def test_start(monkeypatch: pytest.MonkeyPatch):
    """Test that the charm has the correct state after handling the start event."""
    # Arrange:
    ctx = testing.Context(PhasedUpdaterOperatorCharm)
    monkeypatch.setattr("charm.phased_updater.get_version", mock_get_version)
    # Act:
    state_out = ctx.run(ctx.on.start(), testing.State())
    # Assert:
    assert state_out.workload_version is not None
    assert state_out.unit_status == testing.ActiveStatus()

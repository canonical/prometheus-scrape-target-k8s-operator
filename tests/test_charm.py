# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

from ops.testing import Harness

from charm import PrometheusScrapeTargetCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        """Flake8 forces me to write meaningless docstrings."""
        self.harness = Harness(PrometheusScrapeTargetCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

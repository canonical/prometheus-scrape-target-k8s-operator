# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

from charm import PrometheusScrapeTargetCharm
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(PrometheusScrapeTargetCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()


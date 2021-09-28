# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness

from charm import PrometheusScrapeTargetCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        """Flake8 forces me to write meaningless docstrings."""
        self.harness = Harness(PrometheusScrapeTargetCharm)
        self.harness.set_model_info(name="lma", uuid="e40bf1a0-91f4-45a5-9f35-eb30fd010e4d")
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_no_data(self):
        """Test charm is blocked when no configs are provided."""
        self.harness.set_leader(True)

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")

        self.assertEqual(
            {},
            self.harness.get_relation_data(downstream_rel_id, self.harness.charm.app.name),
        )

        self.assertEqual(self.harness.model.unit.status, BlockedStatus("No targets specified"))

    def test_no_labels(self):
        """Test relation data for single targets without additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo:1234,bar:5678"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")

        self.assertEqual(
            {
                "scrape-jobs": [
                    {
                        "job_name": "external_jobs",
                        "metrics_path": "/metrics",
                        "static_configs": [
                            {
                                "targets": ["foo:1234", "bar:5678"],
                                "labels": [],
                            },
                        ],
                    }
                ]
            },
            self.harness.get_relation_data(downstream_rel_id, self.harness.charm.app.name),
        )

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_with_labels(self):
        """Test relation data for single targets with additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config(
            {
                "targets": "foo:1234,bar:5678",
                "labels": "lfoo:lbar",
                "metrics-path": "/foometrics",
            }
        )

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")

        self.assertEqual(
            {
                "scrape-jobs": [
                    {
                        "job_name": "external_jobs",
                        "metrics_path": "/foometrics",
                        "static_configs": [
                            {
                                "targets": ["foo:1234", "bar:5678"],
                                "labels": {"lfoor": "lbar"},
                            },
                        ],
                    }
                ]
            },
            self.harness.get_relation_data(downstream_rel_id, self.harness.charm.app.name),
        )

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

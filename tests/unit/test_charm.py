# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import json
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

    def test_no_leader(self):
        """Test no relation data changes if agent is not leader."""
        self.harness.set_leader(False)

        self.harness.update_config({"targets": "foo:1234,bar:5678"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual({}, relation_data)

    def test_no_labels(self):
        """Test relation data for single targets without additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo:1234,bar:5678"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual(["scrape_jobs"], list(relation_data.keys()))
        self.assertEqual(
            [
                {
                    "job_name": "juju_lma_e40bf1a_prometheus-scrape-target-k8s_external_jobs",
                    "metrics_path": "/metrics",
                    "static_configs": [
                        {
                            "targets": ["foo:1234", "bar:5678"],
                            # "labels": {},
                        },
                    ],
                }
            ],
            json.loads(relation_data["scrape_jobs"]),
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
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        # Ensure we have no other key set, specifically we do not want any `scrape_metadata`
        self.assertEqual(["scrape_jobs"], list(relation_data.keys()))
        self.assertEqual(
            [
                {
                    "job_name": "juju_lma_e40bf1a_prometheus-scrape-target-k8s_external_jobs",
                    "metrics_path": "/foometrics",
                    "static_configs": [
                        {
                            "targets": ["foo:1234", "bar:5678"],
                            "labels": {"lfoo": "lbar"},
                        },
                    ],
                }
            ],
            json.loads(relation_data["scrape_jobs"]),
        )

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_valid_target_without_port(self):
        """Test relation data for single targets without additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo,bar"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual(["scrape_jobs"], list(relation_data.keys()))
        self.assertEqual(
            [
                {
                    "job_name": "juju_lma_e40bf1a_prometheus-scrape-target-k8s_external_jobs",
                    "metrics_path": "/metrics",
                    "static_configs": [
                        {
                            "targets": ["foo:80", "bar:80"],
                            # "labels": {},
                        },
                    ],
                }
            ],
            json.loads(relation_data["scrape_jobs"]),
        )

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_invalid_host_with_scheme(self):
        """Test relation data for single targets without additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "https://foo:1234"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual([], list(relation_data.keys()))
        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)

    def test_invalid_host_with_path(self):
        """Test relation data for single targets without additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo:1234/ahah"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual([], list(relation_data.keys()))
        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)

    def test_invalid_port(self):
        """Test relation data for targets with invalid address."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo:123456789,bar:5678"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)
        self.assertEqual({}, dict(relation_data))

# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import json
import unittest

from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.testing import Harness

from charm import PrometheusScrapeTargetCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        """Flake8 forces me to write meaningless docstrings."""
        self.harness = Harness(PrometheusScrapeTargetCharm)
        self.harness.set_model_info(name="lma", uuid="e40bf1a0-91f4-45a5-9f35-eb30fd010e4d")
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_charm_blocks_if_no_targets_specified(self):
        """Test charm is blocked when no configs are provided."""
        self.harness.set_leader(True)

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")

        self.assertEqual(
            {"scrape_jobs": "[]"},
            self.harness.get_relation_data(downstream_rel_id, self.harness.charm.app.name),
        )

        self.assertEqual(self.harness.model.unit.status, BlockedStatus("No targets specified"))

    def test_non_leader_does_not_modify_relation_data(self):
        """Test no relation data changes if agent is not leader."""
        self.harness.set_leader(False)

        self.harness.update_config({"targets": "foo:1234,bar:5678"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual({}, relation_data)

    def test_scrape_job_has_no_labels_if_not_specified(self):
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

    def test_scrape_job_has_specified_labels(self):
        """Test relation data for single targets with additional labels."""
        self.harness.set_leader(True)

        self.harness.update_config(
            {
                "targets": "foo:1234,bar:5678",
                "labels": "lfoo:lbar",
                "metrics_path": "/foometrics",
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

    def test_scrape_job_has_no_port_if_not_specified(self):
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
                    "static_configs": [
                        {
                            "targets": ["foo", "bar"],
                            # "labels": {},
                        },
                    ],
                }
            ],
            json.loads(relation_data["scrape_jobs"]),
        )

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_charm_blocks_if_target_includes_scheme(self):
        """Test the charm goes into blocked state if provided target address includes a scheme."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "https://foo:1234"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual({"scrape_jobs": "[]"}, relation_data)
        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)

    def test_charm_blocks_if_target_includes_path(self):
        """Test the charm goes into blocked state if provided target address includes a path."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo:1234/ahah"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertEqual({"scrape_jobs": "[]"}, relation_data)
        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)

    def test_charm_blocks_if_specified_port_invalid(self):
        """Test the charm goes into blocked state if provided port number is invalid."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "foo:123456789,bar:5678"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)
        self.assertEqual({"scrape_jobs": "[]"}, dict(relation_data))

    def test_non_leader_unit_sets_waiting_status(self):
        """Test units that are not leader are marked inactive."""
        self.harness.set_leader(False)

        self.harness.update_config({"targets": "https://192.186.1.0:1234"})

        self.assertEqual(self.harness.model.unit.status, WaitingStatus("inactive unit"))

    def test_charm_removes_job_when_empty_targets_are_specified(self):
        """Test the charm removes existing jobs and target list set to an empty value."""
        self.harness.set_leader(True)

        self.harness.update_config({"targets": "192.168.1.1:8000"})

        downstream_rel_id = self.harness.add_relation("metrics-endpoint", "prometheus-k8s")
        relation_data = self.harness.get_relation_data(
            downstream_rel_id, self.harness.charm.app.name
        )

        expected_jobs = {
            "scrape_jobs": '[{"job_name": '
            '"juju_lma_e40bf1a_prometheus-scrape-target-k8s_external_jobs", '
            '"static_configs": [{"targets": ["192.168.1.1:8000"]}]}]'
        }

        self.assertIsInstance(self.harness.model.unit.status, ActiveStatus)
        self.assertEqual(expected_jobs, relation_data)

        self.harness.update_config({"targets": ""})

        self.assertIsInstance(self.harness.model.unit.status, BlockedStatus)
        self.assertEqual({"scrape_jobs": "[]"}, dict(relation_data))

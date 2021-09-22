#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Prometheus Scrape Target Charm.
"""

import json
import logging
import re

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)

# default port for scrape targets
DEFAULT_PORT = 80


class PrometheusScrapeTargetCharm(CharmBase):
    """Prometheus Scrape Target Charm."""

    def __init__(self, *args):
        super().__init__(*args)

        self._prometheus_relation = "metrics-endpoint"

        # handle changes in relation with Prometheus
        self.framework.observe(self.on[self._prometheus_relation].relation_joined,
                               self._update_prometheus_jobs)
        self.framework.observe(self.on[self._prometheus_relation].relation_changed,
                               self._update_prometheus_jobs)

        # handle changes in external scrape targets
        self.framework.observe(self.on.config_changed, self._update_prometheus_jobs)

    def _update_prometheus_jobs(self, _):
        """Setup Prometheus scrape configuration for external targets.
        """
        self.unit.status = ActiveStatus()
        if not self.unit.is_leader():
            return

        jobs = self._scrape_jobs()
        if not jobs:
            return

        for relation in self.model.relations[self._prometheus_relation]:
            relation.data[self.app]["scrape_jobs"] = json.dumps(jobs)

    def _scrape_jobs(self):
        if not (targets := self.model.config.get("targets", "")):
            return []

        urls = targets.split(",")
        targets = []
        invalid_targets = []
        for url in urls:
            if not (valid_address := self._validated_address(url)):
                invalid_targets.append(url)
                continue
            targets.append(valid_address)

        if invalid_targets:
            self.unit.status = BlockedStatus(f"Invalid targets : {invalid_targets}")

        jobs = [
            {
                "job_name": self._job_name(),
                "metrics_path": self.model.config["metrics-path"],
                "static_configs": [
                    {
                        "targets": targets,
                        "labels": self._labels()
                    }
                ]
            }
        ] if targets else []

        return jobs

    def _validated_address(self, address):
        # split host and port parts
        num_colons = address.count(":")
        if num_colons > 1:
            return ""
        host, port = address.split(":") if num_colons else (address, DEFAULT_PORT)

        # validate port
        try:
            port = int(port)
        except ValueError:
            return ""

        if port < 0 or port > 2**16-1:
            return ""

        # validate host
        match = re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host.strip())
        if not match:
            return ""
        else:
            return f"{match.group(0)}:{port}"

    def _labels(self):
        if not (all_labels := self.model.config.get("labels", "")):
            return {}

        labels = {}
        invalid_labels = []
        for label in all_labels.split(","):
            try:
                key, value = label.split(":")
            except ValueError:
                invalid_labels.append(label)
                continue

            if key and value:
                labels[key] = value
            else:
                invalid_labels.append(f"{key}:{value}")

        if invalid_labels:
            self.unit.status = BlockedStatus(f"Invalid labels : {invalid_labels}")

        return labels

    def _job_name(self):
        return "juju_{}_{}_{}_{}".format(
            self.model.name,
            self.model.uuid[:7],
            self.app.name,
            self.model.config["job-name"]
        )


if __name__ == "__main__":
    main(PrometheusScrapeTargetCharm)

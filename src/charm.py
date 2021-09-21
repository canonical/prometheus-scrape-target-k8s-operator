#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Prometheus Scrape Target Charm.
"""

import json
import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


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
        jobs = [
            {
                "job_name": self._job_name(),
                "metrics_path": self.model.config["metrics-path"],
                "static_configs": [
                    {
                        "targets": [str(urlsplit(url).netloc) for url in urls],
                        "labels": self._labels()
                    }
                ]
            }
        ]

        return jobs

    def _labels(self):
        if not (all_labels := self.model.config.get("labels", "")):
            return {}

        labels = {}
        for label in all_labels.split(","):
            key, value = label.split(":")
            if key and value:
                labels[key] = value

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

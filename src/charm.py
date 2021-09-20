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
from urllib.parse import urlparse

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

        jobs = []
        urls = targets.split(",")
        for url in urls:
            parsed_url = urlparse(url)

            if not (parsed_url.netloc):
                continue

            job = {
                "metrics_path": parsed_url.path if parsed_url.path else "/metrics",
                "static_configs": [
                    {
                        "targets": [str(parsed_url.netloc)],
                        "labels": self._labels()
                    }
                ]
            }
            jobs.append(job)

        return jobs

    def _labels(self):
        if not (label_pairs := self.model.config.get("labels", "")):
            return {}

        labels = {}
        for label in label_pairs:
            key, value = label.split(":")
            if key and value:
                labels[key] = value

        return labels


if __name__ == "__main__":
    main(PrometheusScrapeTargetCharm)

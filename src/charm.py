#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Prometheus Scrape Target Charm."""

import logging
import re

from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)

# default port for scrape targets
DEFAULT_METRICS_ENDPOINT_PORT = 80


def _validated_address(address):
    # split host and port parts
    num_colons = address.count(":")
    if num_colons > 1:
        return ""
    host, port = address.split(":") if num_colons else (address, DEFAULT_METRICS_ENDPOINT_PORT)

    # validate port
    try:
        port = int(port)
    except ValueError:
        return ""

    if port < 0 or port > 2 ** 16 - 1:
        return ""

    # validate host
    match = re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host.strip())
    if not match:
        return ""
    else:
        return f"{match.group(0)}:{port}"


class PrometheusScrapeTargetCharm(CharmBase):
    """Prometheus Scrape Target Charm."""

    def __init__(self, *args):
        super().__init__(*args)

        self.metrics_endpoint = MetricsEndpointProvider(
            self, "metrics-endpoint", self.on.config_changed, jobs=self._scrape_jobs()
        )

        self.unit.status = ActiveStatus()

    def _scrape_jobs(self):
        if targets := self._targets():
            jobs = [
                {
                    "job_name": self._job_name(),
                    "metrics_path": self.model.config["metrics-path"],
                    "static_configs": [
                        {
                            "targets": targets,
                        }
                    ],
                }
            ]

            if labels := self._labels():
                jobs[0]["static_configs"][0]["labels"] = labels

            return jobs
        return []

    def _targets(self):
        if not (targets := self.model.config.get("targets", "")):
            return []

        urls = targets.split(",")
        targets = []
        invalid_targets = []
        for url in urls:
            if not (valid_address := _validated_address(url)):
                invalid_targets.append(url)
                continue
            targets.append(valid_address)

        if invalid_targets:
            self.unit.status = BlockedStatus(f"Invalid targets : {invalid_targets}")

        return targets

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
            self.model.name, self.model.uuid[:7], self.app.name, self.model.config["job-name"]
        )


if __name__ == "__main__":
    main(PrometheusScrapeTargetCharm)

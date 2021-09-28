#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Prometheus Scrape Target Charm."""

import json
import logging
import re

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)

# default port for scrape targets
DEFAULT_METRICS_ENDPOINT_PORT = 80


class PrometheusScrapeTargetCharm(CharmBase):
    """Prometheus Scrape Target Charm."""

    def __init__(self, *args):
        super().__init__(*args)

        self._prometheus_relation = "metrics-endpoint"

        # handle changes in relation with Prometheus
        self.framework.observe(
            self.on[self._prometheus_relation].relation_created, self._update_prometheus_jobs
        )
        self.framework.observe(
            self.on[self._prometheus_relation].relation_changed, self._update_prometheus_jobs
        )

        # handle changes in external scrape targets
        self.framework.observe(self.on.config_changed, self._update_prometheus_jobs)

    def _update_prometheus_jobs(self, _):
        """Setup Prometheus scrape configuration for external targets."""
        if self.unit.is_leader():
            if jobs := self._scrape_jobs():
                for relation in self.model.relations[self._prometheus_relation]:
                    relation.data[self.app]["scrape_jobs"] = json.dumps(jobs)

                self.unit.status = ActiveStatus()

    def _scrape_jobs(self):
        targets = self._targets()
        labels = self._labels()

        return (
            [
                {
                    "job_name": self._job_name(),
                    "metrics_path": self.model.config["metrics-path"],
                    "static_configs": [
                        {
                            "targets": targets,
                            "labels": labels,
                        }
                    ],
                }
            ]
            if targets
            else []
        )

    def _targets(self):
        if not (config_targets := self.model.config.get("targets", "")):
            self.unit.status = BlockedStatus("No targets specified")
            return []

        targets = []
        invalid_targets = []
        for config_target in config_targets.split(","):
            valid_address = self._validated_address(config_target)

            if valid_address:
                targets.append(valid_address)
            else:
                invalid_targets.append(valid_address)

        if invalid_targets:
            logger.error("Invalid targets found: %s", invalid_targets)
            self.unit.status = BlockedStatus(f"Invalid targets : {invalid_targets}")
            return []

        return targets

    def _validated_address(self, address):
        # split host and port parts
        num_colons = address.count(":")
        if num_colons > 1:
            logger.error("No ':' in target: %s", address)
            return ""

        host, port = address.split(":") if num_colons else (address, DEFAULT_METRICS_ENDPOINT_PORT)

        # validate port
        try:
            port = int(port)
        except ValueError:
            logger.error("Invalid port for target: %s", port)
            return ""

        if port < 0 or port > 2 ** 16 - 1:
            logger.error("Invalid port range for target: %s", port)
            return ""

        # validate host
        match = re.search(
            r"^(?:(?:(?:(?:[a-zA-Z0-9][-a-zA-Z0-9]*)?[a-zA-Z0-9])[.])*(?:[a-zA-Z][-a-zA-Z0-9]*[a-zA-Z0-9]|[a-zA-Z])[.]?)$",
            host.strip(),
        )

        if not match:
            logger.error("Invalid hostname: %s", host.strip())
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
            self.model.name, self.model.uuid[:7], self.app.name, self.model.config["job-name"]
        )


if __name__ == "__main__":
    main(PrometheusScrapeTargetCharm)

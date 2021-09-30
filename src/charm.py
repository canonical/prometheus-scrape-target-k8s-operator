#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Prometheus Scrape Target Charm."""

import json
import logging
from urllib.parse import urlparse

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)

# default port for scrape targets
DEFAULT_METRICS_ENDPOINT_PORT = 80


def _validated_address(address: str) -> str:
    """Validate address using urllib.parse.urlparse.

    Args:
        address: must not include scheme.
    """
    # Add '//' prefix per RFC 1808, if not already there
    # This is needed by urlparse, https://docs.python.org/3/library/urllib.parse.html
    if not address.startswith("//"):
        address = "//" + address

    parsed = urlparse(address)
    if not parsed.netloc or any([parsed.scheme, parsed.path, parsed.params, parsed.query]):
        logger.error("Invalid address (should only include netloc): %s", address)
        return ""

    # validate port
    try:
        if parsed.port is not None:
            target = parsed.netloc
        else:
            target = f"{parsed.netloc}:{DEFAULT_METRICS_ENDPOINT_PORT}"
    except ValueError:
        logger.error("Invalid port for target: %s", parsed.netloc)
        return ""

    return target


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
        if not self.unit.is_leader():
            return

        if jobs := self._scrape_jobs():
            for relation in self.model.relations[self._prometheus_relation]:
                relation.data[self.app]["scrape_jobs"] = json.dumps(jobs)

            self.unit.status = ActiveStatus()

    def _scrape_jobs(self) -> list:
        if targets := self._targets():
            static_config = {"targets": targets}
            if labels := self._labels():
                static_config.update(labels=labels)

            return [
                {
                    "job_name": self._job_name(),
                    "metrics_path": self.model.config["metrics-path"],
                    "static_configs": [static_config],
                }
            ]

        return []

    def _targets(self) -> list:
        if not (unvalidated_scrape_targets := self.model.config.get("targets", "")):
            self.unit.status = BlockedStatus("No targets specified")
            return []

        targets = []
        invalid_targets = []
        for config_target in unvalidated_scrape_targets.split(","):
            if valid_address := _validated_address(config_target):
                targets.append(valid_address)
            else:
                invalid_targets.append(config_target)

        if invalid_targets:
            logger.error("Invalid targets found: %s", invalid_targets)
            self.unit.status = BlockedStatus(f"Invalid targets : {invalid_targets}")
            return []

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

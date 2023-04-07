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
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

logger = logging.getLogger(__name__)


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
        logger.error("Invalid address : %s", address)
        logger.error("Targets must be specified in host:port format")
        return ""

    # validate port
    try:
        # the port property would raise an exception if the port is invalid
        _ = parsed.port
        target = parsed.netloc
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

        # Sometimes a `stop` event is followed by a `start` event with nothing in between
        # https://bugs.launchpad.net/juju/+bug/2015566
        self.framework.observe(self.on.start, self._update_prometheus_jobs)

        # One time charm setup
        self.framework.observe(self.on.install, self._on_install)

    def _on_install(self, _) -> None:
        """Initial charm setup."""
        self.unit.set_workload_version("n/a")

    def _update_prometheus_jobs(self, _):
        """Setup Prometheus scrape configuration for external targets."""
        if not self.unit.is_leader():
            self.unit.status = WaitingStatus("inactive unit")
            return

        jobs = self._scrape_jobs()
        for relation in self.model.relations[self._prometheus_relation]:
            relation.data[self.app]["scrape_jobs"] = json.dumps(jobs)

        if jobs:
            self.unit.status = ActiveStatus()
        else:
            self.unit.status = BlockedStatus("No targets specified")

    def _scrape_jobs(self) -> list:  # noqa: C901
        if targets := self._targets():
            static_config = {"targets": targets}
            if labels := self._labels():
                static_config.update(labels=labels)

            job = {
                "job_name": self._job_name(),
                "static_configs": [static_config],
            }

            for option in (
                "metrics_path",  # prom's built-in default: [ metrics_path: <path> | default = /metrics ]
                "scheme",
            ):
                if value := self.model.config.get(option):
                    job.update({option: value})

            tls_config = {}
            if ca_file := self.model.config.get("tls_config_ca_file"):
                tls_config.update({"ca_file": ca_file})
            if insecure_skip_verify := self.model.config.get("tls_config_insecure_skip_verify"):
                # Need to convert bool to lowercase str
                tls_config.update({"insecure_skip_verify": insecure_skip_verify})
            if tls_config:
                job.update({"tls_config": tls_config})

            if basic_auth := self.model.config.get("basic_auth"):
                try:
                    username, password = basic_auth.split(":")
                except ValueError:
                    self.unit.status = BlockedStatus(
                        "Invalid basic_auth config option; use `user:password` format"
                    )
                else:
                    job.update({"basic_auth": {"username": username, "password": password}})

            return [job]

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
            logger.error("Targets must be specified in host:port format")
            self.unit.status = BlockedStatus("Invalid targets, see debug-logs")
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
            logger.error("Invalid labels : %s", invalid_labels)
            logger.error("Labels must be specified in key:value format")
            self.unit.status = BlockedStatus("Invalid labels, see debug-logs")
        return labels

    def _job_name(self):
        return "juju_{}_{}_{}_{}".format(
            self.model.name, self.model.uuid[:7], self.app.name, self.model.config["job_name"]
        )


if __name__ == "__main__":
    main(PrometheusScrapeTargetCharm)

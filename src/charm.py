#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Prometheus Scrape Target Charm.
"""

import logging

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus

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


if __name__ == "__main__":
    main(PrometheusScrapeTargetCharm)

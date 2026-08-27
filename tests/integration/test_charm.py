#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

from __future__ import annotations

import json
import logging
import pathlib
import urllib.request

import jubilant
import pytest
import yaml
from jubilant import Juju

log = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text())


@pytest.mark.abort_on_fail
def test_build_and_deploy(juju: Juju, charm: pathlib.Path):
    """Deploy the charm-under-test together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    juju.deploy(charm, app="st")

    # deploy prometheus from dev/edge
    juju.deploy("prometheus-k8s", app="prom", channel="dev/edge", trust=True)

    # wait for charms to settle; without any config, the charm should be blocked
    juju.wait(
        lambda status: (
            jubilant.all_blocked(status, "st")
            and jubilant.all_active(status, "prom")
            and jubilant.all_agents_idle(status, "st", "prom")
        ),
        timeout=1000,
    )


@pytest.mark.abort_on_fail
def test_unconfigured_scrape_config_does_not_affect_prometheus(juju: Juju):
    juju.integrate("prom:metrics-endpoint", "st:metrics-endpoint")
    juju.wait(
        lambda status: (
            jubilant.all_active(status, "prom") and jubilant.all_agents_idle(status, "prom", "st")
        ),
        timeout=1000,
    )


@pytest.mark.abort_on_fail
def test_scrape_config_is_ingested_by_prometheus(juju: Juju):
    address = juju.status().apps["prom"].units["prom/0"].address
    url = f"http://{address}:9090"
    log.debug("prom public address: %s", url)

    juju.config("st", {"targets": "1.2.3.4"})
    juju.wait(
        lambda status: (
            jubilant.all_active(status, "prom", "st")
            and jubilant.all_agents_idle(status, "prom", "st")
        ),
        timeout=1000,
    )

    def get_prom_config(url: str) -> dict:
        response = urllib.request.urlopen(f"{url}/api/v1/status/config", data=None, timeout=10.0)
        assert response.code == 200
        data = json.loads(response.read())
        config = yaml.safe_load(data["data"]["yaml"])
        # {
        #     "global": {
        #         "scrape_interval": "1m",
        #         "scrape_timeout": "10s",
        #         "evaluation_interval": "1m",
        #     },
        #     "rule_files": ["/etc/prometheus/rules/juju_*.rules"],
        #     "scrape_configs": [
        #         {
        #             "job_name": "prometheus",
        #             "honor_timestamps": True,
        #             "scrape_interval": "5s",
        #             "scrape_timeout": "5s",
        #             "metrics_path": "/metrics",
        #             "scheme": "http",
        #             "static_configs": [{"targets": ["localhost:9090"]}],
        #         },
        #         {
        #             "job_name": "juju_test-prometheus-b1rn_1a497e3_st_external_jobs",
        #             "honor_timestamps": True,
        #             "scrape_interval": "1m",
        #             "scrape_timeout": "10s",
        #             "metrics_path": "/metrics",
        #             "scheme": "http",
        #             "static_configs": [{"targets": ["1.2.3.4"]}],
        #         },
        #     ],
        # }
        log.debug("config: %s", config)
        return config

    # get data from prometheus
    scrape_configs: list = get_prom_config(url)["scrape_configs"]

    ours = list(
        filter(
            lambda scrape_config: scrape_config["static_configs"][0]["targets"] == ["1.2.3.4"],
            scrape_configs,
        )
    )
    assert len(ours) == 1

    # update config and retest
    juju.config("st", {"targets": "1.2.3.4:5678", "metrics_path": "/foometrics"})
    juju.wait(
        lambda status: (
            jubilant.all_active(status, "prom", "st")
            and jubilant.all_agents_idle(status, "prom", "st")
        ),
        timeout=1000,
    )

    scrape_configs = get_prom_config(url)["scrape_configs"]
    ours = list(
        filter(
            lambda scrape_config: (
                scrape_config["static_configs"][0]["targets"] == ["1.2.3.4:5678"]
            ),
            scrape_configs,
        )
    )
    assert len(ours) == 1
    assert ours[0]["metrics_path"] == "/foometrics"

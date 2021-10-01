#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import json
import logging
import urllib.request
from pathlib import Path

import pytest
import yaml
from helpers import get_unit_address  # type: ignore[attr-defined]

log = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # build and deploy charm from local source folder
    charm_under_test = await ops_test.build_charm(".")
    resources = {"unused-image": METADATA["resources"]["unused-image"]["upstream-source"]}
    await ops_test.model.deploy(charm_under_test, resources=resources, application_name="st")

    # deploy prometheus from edge
    await ops_test.model.deploy("prometheus-k8s", application_name="prom", channel="edge")

    # wait for charms to settle
    await ops_test.model.wait_for_idle(apps=["st", "prom"], timeout=1000)

    # without any config, the charm should be blocked
    assert ops_test.model.applications["st"].units[0].workload_status == "blocked"


@pytest.mark.abort_on_fail
async def test_unconfigured_scrape_config_does_not_affect_prometheus(ops_test):
    # relate prometheus to this charm
    await ops_test.model.applications["prom"].add_relation(
        "metrics-endpoint", "st:metrics-endpoint"
    )
    await ops_test.model.wait_for_idle(apps=["prom"], status="active", timeout=1000)
    assert ops_test.model.applications["prom"].units[0].workload_status == "active"


@pytest.mark.abort_on_fail
async def test_scrape_config_is_ingested_by_prometheus(ops_test):
    address = await get_unit_address(ops_test, "prom", 0)
    url = f"http://{address}:9090"
    log.debug("prom public address: %s", url)

    await ops_test.model.applications["st"].set_config({"targets": "1.2.3.4"})
    await ops_test.model.wait_for_idle(apps=["prom", "st"], status="active")

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
    await ops_test.model.applications["st"].set_config(
        {"targets": "1.2.3.4:5678", "metrics-path": "/foometrics"}
    )
    await ops_test.model.wait_for_idle(apps=["prom", "st"], status="active")

    scrape_configs: list = get_prom_config(url)["scrape_configs"]
    ours = list(
        filter(
            lambda scrape_config: scrape_config["static_configs"][0]["targets"]
            == ["1.2.3.4:5678"],
            scrape_configs,
        )
    )
    assert len(ours) == 1
    assert ours[0]["metrics_path"] == "/foometrics"

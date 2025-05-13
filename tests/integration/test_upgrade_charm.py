#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
from pathlib import Path

import pytest
import sh
import yaml
from helpers import get_config_values

# pyright: reportAttributeAccessIssue = false

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
app_name = METADATA["name"]


# FIXME Uncomment after merge @pytest.mark.abort_on_fail
@pytest.mark.xfail
async def test_config_values_are_retained_after_pod_upgraded(ops_test, charm_under_test):
    """Deploy from charmhub and then upgrade with the charm-under-test."""
    logger.info("deploy charm from charmhub")
    sh.juju.deploy(app_name, model=ops_test.model.name, channel="edge")

    config = {"targets": "1.2.3.4:5678", "metrics_path": "/foometrics"}
    await ops_test.model.wait_for_idle(apps=[app_name], status="blocked", timeout=1000)
    await ops_test.model.applications[app_name].set_config(config)
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)

    logger.info("upgrade deployed charm with local charm %s", charm_under_test)
    sh.juju.refresh(app_name, model=ops_test.model.name, path=charm_under_test)
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)

    assert (await get_config_values(ops_test, app_name)).items() >= config.items()

# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

log = logging.getLogger(__name__)


async def get_unit_address(ops_test, app_name: str, unit_num: int) -> str:
    status = await ops_test.model.get_status()  # noqa: F821
    return status["applications"][app_name]["units"][f"{app_name}/{unit_num}"]["address"]


async def get_config_values(ops_test, app_name) -> dict:
    """Return the app's config, but filter out keys that do not have a value."""
    config = await ops_test.model.applications[app_name].get_config()
    return {key: config[key]["value"] for key in config if "value" in config[key]}

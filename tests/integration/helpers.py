# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

from jubilant import Juju

log = logging.getLogger(__name__)


def get_unit_address(juju: Juju, app_name: str, unit_num: int) -> str:
    status = juju.status()
    return status.apps[app_name].units[f"{app_name}/{unit_num}"].address


def get_config_values(juju: Juju, app_name: str) -> dict:
    """Return the app's config, but filter out keys that do not have a value."""
    return dict(juju.config(app_name) or {})

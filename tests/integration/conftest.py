#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

from __future__ import annotations

import logging
import os
from pathlib import Path

import sh  # type: ignore[import-untyped]
from pytest import fixture

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent


def pack(root: Path) -> Path:
    """Pack a local charm and return it."""
    # charmcraft outputs "Packed <charm_file>" lines to stderr
    charmcraft = sh.Command("charmcraft")
    output = charmcraft.pack("-p", str(root), _err_to_out=True)

    packed_charms = [
        line.split()[1] for line in str(output).strip().splitlines() if line.startswith("Packed")
    ]

    if not packed_charms:
        raise ValueError(f"Unable to get packed charm from charmcraft output: {output}")

    return Path(packed_charms[0]).resolve()


@fixture(scope="session")
def charm() -> Path:
    """Packed charm used for integration testing: ``CHARM_PATH``, else a fresh pack."""
    if charm_file := os.environ.get("CHARM_PATH"):
        return Path(charm_file).resolve()

    charms = list(REPO_ROOT.glob("*.charm"))
    if charms:
        assert len(charms) == 1, f"Found more than one charm, cannot pick: {charms}"
        return charms[0].resolve()

    logger.info("packing charm from %s", REPO_ROOT)
    return pack(REPO_ROOT)

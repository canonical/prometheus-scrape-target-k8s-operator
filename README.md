# Prometheus Scrape Target Operator

[![CharmHub Badge](https://charmhub.io/prometheus-scrape-target-k8s/badge.svg)](https://charmhub.io/prometheus-scrape-target-k8s)
[![Release](https://github.com/canonical/prometheus-scrape-target-k8s-operator/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/prometheus-scrape-target-k8s-operator/actions/workflows/release.yaml)
[![Discourse Status](https://img.shields.io/discourse/status?server=https%3A%2F%2Fdiscourse.charmhub.io&style=flat&label=CharmHub%20Discourse)](https://discourse.charmhub.io)

## Description

The Prometheus Scrape Target operator supports metrics aggregation
from applications outside any Juju model. This facilitates using the
[Canonical Observability Stack](https://charmhub.io/cos-lite) even for
use cases where the metrics endpoints do not originate from other
[charmed operators](https://charmhub.io/).

## Usage

```sh
# Deploy prometheus, scrape target charms and relate them
$ juju deploy prometheus-k8s
$ juju deploy prometheus-scrape-target-k8s
$ juju relate prometheus-k8s prometheus-scrape-target-k8s

# Setup http://192.168.5.2:7000 as an external target
juju config prometheus-scrape-target targets="192.168.5.2:7000"
```

## Relations

- [Prometheus](https://charmhub.io/prometheus-k8s) The scrape target
  charm only supports relations with a metrics consumer charm using the
  `metrics-endpoint` relation and the `prometheus_scrape` interface.

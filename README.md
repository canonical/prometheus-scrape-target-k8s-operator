# Prometheus Scrape Target Operator

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
juju config prometheus-scrape-target targets="http://192.168.5.2:7000"
```

## Relations

- [Prometheus](https://charmhub.io/prometheus-k8s) The scrape target
  charm only supports relations with a metrics consumer charm using the
  `metrics-endpoint` relation and the `prometheus_scrape` interface.

## OCI Images

The Prometheus scrape target operator does not manage a work load and
hence does not need a specific OCI Image. It does use a "dummy" image
which can be substituted for using any small lightweight container,
for example such as [busybox](https://hub.docker.com/_/busybox/).

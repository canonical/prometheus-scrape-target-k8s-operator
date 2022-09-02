# Prometheus Scrape Target Operator

## Description

The Prometheus Scrape Target operator supports metrics aggregation
from applications outside any Juju model. This facilitates using the
[Canonical Observability Stack](https://charmhub.io/cos-lite) even for
use cases where the metrics endpoints do not originate from other
[charmed operators](https://charmhub.io/).

## Usage

First, deploy the prometheus and the scrape target charms

```sh
$ juju deploy prometheus-k8s
$ juju deploy prometheus-scrape-target-k8s
```

Then, relate the charms together.

```sh
$ juju relate prometheus-k8s prometheus-scrape-target-k8s
```

Last, configure the scrape target charm, adding
`http://192.168.5.2:7000` as an external scrape target

```sh
$ juju config \
    prometheus-scrape-target \
    targets="192.168.5.2:7000"
```

## Relations

- A `metrics-endpoint` relation with a charm that implements the
  `prometheus_scrape` interface as a consumer, like [Prometheus](https://charmhub.io/prometheus-k8s).

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) as well as
[`CONTRIBUTING.md`](CONTRIBUTING.md) for more information on how to
contribute to this charm.

# Contributing

## Overview

This documents explains the processes and practices recommended for
contributing enhancements to the Prometheus Scrape Target charm.

- Generally, before developing enhancements to this charm, you should consider
  [opening an issue ](https://github.com/canonical/prometheus-scrape-target-k8s-operator)
  explaining your use case.
- If you would like to chat with us about your use-cases or proposed
  implementation, you can reach us at
  [Canonical Mattermost public channel](https://chat.charmhub.io/charmhub/channels/charm-dev)
  or [Discourse](https://discourse.charmhub.io/).
  The primary author of this charm is available on the Mattermost channel as
  `@balbir-thomas`.
- Familiarising yourself with the
  [Charmed Operator Framework](https://juju.is/docs/sdk)
  library will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review
  typically examines
  + code quality
  + test coverage
  + user experience for Juju administrators
- Please help us out in ensuring easy to review branches by rebasing
  your pull request branch onto the `main` branch. This also avoids
  merge commits and creates a linear Git commit history.

## Developing

Create and activate a virtualenv with the development requirements:

```bash
$ virtualenv -p python3 venv
$ source venv/bin/activate
```

### Charm Specific Setup

A typical setup using [Snap](https://snapcraft.io/), for deployments
to a [microk8s](https://microk8s.io/) cluster can be achieved by
following instructions in the Juju SDK
[development setup](https://juju.is/docs/sdk/dev-setup).


### Build

Build the charm in this git repository

```bash
$ charmcraft pack
```

### Deploy

```bash
$ juju deploy ./prometheus-scrape-target-k8s_ubuntu-20.04-amd64.charm --resource unused-image=busybox:latest
```

## Linting
Flake8 and black linters may be run to check charm and test source code using the
command

```bash
tox -e lint
```

## Testing

Unit tests are implemented using the Operator Framework test
[harness](https://ops.readthedocs.io/en/latest/#module-ops.testing). These
tests may executed by doing

```bash
$ tox -e unit
```

It is expected that unit tests should provide at least 80% code coverage.

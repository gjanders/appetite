[![Join the chat at https://gitter.im/appetitetalk/Lobby](https://badges.gitter.im/appetitetalk/Lobby.svg)](https://gitter.im/appetitetalk/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Build Status](https://travis-ci.org/Bridgewater/appetite.svg?branch=master)](https://travis-ci.org/Bridgewater/appetite)
[![Coverage Status](https://coveralls.io/repos/github/Bridgewater/appetite/badge.svg?branch=master)](https://coveralls.io/github/Bridgewater/appetite?branch=master)

# Appetite

Extensible services (i.e. Splunk, JIRA) have an ever growing list of apps (includes plugins and add ons).  Managing these apps can be a mess and only gets worse with complexity.  Appetite is a solution that answers the following questions:

1. _Who and when did they install the app?_
1. _What version of the app was installed?_
1. _Did the app actually get installed?_

Appetite was originally designed to deploy applications in Splunk.  It fortuitously started to become more than a Splunk tool and ultimately evolved into becoming a standalone application which can be used ubiquitously across the entire environment.

## Why

For app deployments you typically would use a generic automation tool (chef, puppet, etc).  As the environment becomes more complicated the management of configurations with these tools becomes a major (major) pain.  These generic tools are like swiss army knives - they can do many different things but are the wrong tool for surgery.  A precision tool is needed that does just app deployments very well.  Appetite was created as that precision tool.

Appetite was presented at [Splunk .conf 2016](https://conf.splunk.com/sessions/2016-sessions.html) under the session title **`Unified Open-Sourced Splunk Configuration Management System`**.

[Slides](https://conf.splunk.com/files/2016/slides/unified-open-sourced-splunk-configuration-management-system.pdf)

[Recording](https://conf.splunk.com/files/2016/recordings/unified-open-sourced-splunk-configuration-management-system.mp4)

## What is it?
Appetite is a python based application that is used for generic app deployment.  Here are some of the features:

* Agentless system utilizing a remote server.
* Locks app versions and audits distribution.
* Leverages existing app deployment methods (if specified) and introduces version and tracking meta data.
* Apps are referenced in a manifest file. This file is considered the source of truth for the service.
* Plugin deployments are done under the hood and the user doesn't need to know the specifics of how they are deployed.
* Changing, Adding, and Removing applications are handled automatically.
* Install and update ordering though groups and sites.
* Template variables in files within the app.
* Everything is logged...! This enables end-to-end validation.



## How it works
1. **Monitors manifest changes from repo**

    The git log is checked for manifest changes.  If changes are found then
    Appetite is triggered.

1. **Compares application versions for each host**

    The manifest is broken down to apps per host.  This is then compared to a manifest of current apps on the specified host.

1. **Creates host specific install payloads**

    Based on the manifest breakdown, apps are copied into a compressed payload package along with metadata.

1. **Copy payload to host**

    The host payload is moved to the host machine

1. **Run supplemental command (if given)**

    Run commands that need to happen before the install.

1. **Installs, upgrade, or delete app**

    Based on the deltas logic, apps are deleted first, then changes and adds are applied.

1. **Run supplemental command (if given)**

    For some installs the service might need extra command to run/deploy the apps.
    These are gathered intelligently to call the minimal set of commands.

1. **Restart service if needed**

    If the service needs to be restarted to recognize the app, then restart the service.

## Bon-appetite

Accompanying [Appetite Splunk Application](./splunk/) to parse and analyze Appetite logs.  It was written specifically to visualize applications for a Splunk environment, but can be easily modified to visualize deployments for other applications.

## Supporting Documents

* [Quick Start](./docs/quickstart.md)
* [Configurations](./docs/configurations.md)
* [Changelog](./docs/CHANGELOG.md)
* [Contributing](./docs/contributing.md)
* [Troubleshoot](./docs/troubleshoot.md)

## License

Licensed under the Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
See [LICENSE](./LICENSE).

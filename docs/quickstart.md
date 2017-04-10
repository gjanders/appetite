# Getting Started

Getting Appetite up and running.

1. [Repo](#repo)
2. [Servers](#servers)
3. [Installation](#installation)
4. [Configuration](#configuration)
6. [Scheduled appetite run](#scheduled)


## Repo
<a name="repo"></a>You will need a repo that appetite will use as the source of truth.  A basic repo should be created, the example from the test can be used.

* [How your appetite git repo should look](./git_repo_structure.md)
* [How to write a manifest](./manifest.md)
* [How to configure deployment methods](./deploymentmethods.md) - This for the most part is standard for an application.

## Servers
<a name="servers"></a>There are two types of servers in an Appetite controlled environment.

1. [Application servers](#application_servers) - These are the servers that Appetite will service.
2. [Appetite server](#appetite_server) - This is the server that will run Appetite.

Appetite can run on a application server but it is not recommended because of security posture.

### Application servers
<a name="application_servers"></a>
These are servers that the Appetite server has ssh access to.  DNS is not required but without hostnames it will be harder to keep inventory since the IP addresses would have to be managed.

Examples of the necessary format when using IP addresses can be found in the  [configurations](configurations.md#param_hosts) page.

Example servers given in the [cronjob](../configs/demo_splunk/run_appetite.sh) and [test.py](../script/test/test.py):
The example is the basic setup of a splunk cluster.  You can change the hosts list to your liking.

    HOST_LIST=("splunk-lm001-0c"
               "splunk-cm001-0c"
               "splunk-ds001-0c"
               "splunk-idx001-0c"
               "splunk-idx001-1c"
               "splunk-idx001-2c"
               "splunk-dcs001-0c"
               "splunk-scs001-0c"
               "splunk-scs001-1c")

In the [test.py](../script/test/test.py) these servers are used in the unit testing.

#### Naming convention

Appetite parses out the server class, site and index from the hostname.  All 3 of these variables should be in the hostname.
The naming convention is defined using a jinja2 template.

Example:

        splunk-{{appclass}}{{'%03d'%num}}-{{site}}c"

Variables _appclass_ (string), _num_ (int) and _site_ (str) must exist in the naming convention.

### Appetite server
<a name="appetite_server"></a>
This can be a dedicated or shared instance where Appetite can run.

Complex environments with large configuration repos may require a dedicated host, depending on how often you wish to apply configurations.
For testing repos locally the [--dry-run](./configurations.md#param_dry_run) can be used.

#### Bon_appetit
If you are going to use the **Bon_appetit** Splunk app, the **TA_Appetite** would have to be installed on the Appetite server.

## Installation

### [Docker](https://www.docker.com/)

A [docker container](../Dockerfile) can be created with prerequisites and appetite setup for use.

    docker build -t appetite_server .
    docker run --rm -ti appetite_server

The all configurations and keys located within the appetite directory would be copied too.  Since there is customization required to the configurations before running appetite, the [scheduling](#scheduled) is done manually.

The [docker_test.sh](../tests/docker_tests.sh) script can be used to verify appetite with an install and unit tests.

### Prerequisites
<a name="installation"></a>

* Git
* Python >= 2.7.5
* Python libraries - These are installed using the  [requirements](../script/requirements.txt) file
* Key based SSH access to instances.

### Requirements
<a name="requirements"></a>**Appetite has only been tested on Rhel/Centos systems**

    # Logging directory (default) - Make sure appetite has folder rights to write
    mkdir /var/appetite
    # prereqs for pip packages
    yum install gcc libffi-devel python-devel openssl-devel
    # installs python dependencies
    pip install -r script/requirements.txt

### Installing
Copy the whole appetite project to a folder on the Appetite server.  If everything is loaded correctly then you should be able to run the [unit tests](../script/test/test.py) successfully.

### command line and/or *.conf file setup
Setup can either be done via the command line or a [config file](../configs/demo_splunk/base_apps.conf) **(RECOMMENDED)**. Both methods share the same params.
Command line parameters are always loaded in first, with the config file loaded in afterwards overwriting existing params.
In the config file the first "--" are moved from the param name.

### Examples
A [demo splunk configuration](../configs/demo_splunk) is provided that has examples of config files, [commands.conf](../configs/demo_splunk/commands.conf) and [cronjob](../configs/demo_splunk/run_appetite.sh).

[repo_test.conf](../configs/repo_test.conf) is used for unit testing.  The configuration has dry mode on so there is no ssh communication during the unit tests.

## Scheduling
<a name="scheduled"></a>Appetite can be setup to run on either a cron schedule or via automation tool such as [Jenkins](https://jenkins.io/).
Only a single instance of Appetite will run with other runs prevented due to locking.

Example of Appetite running every 5 mins:

[Open Crontab editor](http://crontab-generator.org/)

    */5 * * * * /opt/appetite/config/demo_splunk/run_appetite.sh


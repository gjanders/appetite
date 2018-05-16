#!/usr/bin/env bash

# This example has hardcoded hosts
#HOST_LIST=("splunk-ds001-0c")
#HOST_LIST=("splunkrandomalias")
HOST_LIST=("splunk-ds-0c:splunkrandomalias","splunk-shm-0c:splunkalias2")
#HOST_LIST=("splunk-shm001-0c:splunkalias2")

HOSTS="${HOST_LIST[@]}"

# Can use inventory scripts to pull hosts.  Example below is for aws.
# HOSTS=$(python ../../src/inventory/aws/get_inv.py --name-query splunk-* --add-quotes)

function appetite_call {
    # $1 -> param config
    appetite_cmd="python ../../src/appetite.py --num-conns 10 --config-file /home/splunk/appetite/configs/demo_splunk/$1.conf --hosts ${HOST_LIST[@]}"
    echo ${appetite_cmd}
    ${appetite_cmd}
}

function run_appetite {
    # Run set of appetite commands
    appetite_call "base_apps"

    #appetite_call "apps"

    #appetite_call "deployment_apps"
}

run_appetite

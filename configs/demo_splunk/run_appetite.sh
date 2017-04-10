#!/usr/bin/env bash

# This example has hardcoded hosts
HOST_LIST=("splunk-lm001-0c"
           "splunk-cm001-0c"
           "splunk-ds001-0c"
           "splunk-idx001-0c"
           "splunk-idx002-0c"
           "splunk-idx003-0c"
           "splunk-idx001-1c"
           "splunk-idx002-1c"
           "splunk-idx003-1c"
           "splunk-sha001-0c"
           "splunk-shm001-0c"
           "splunk-dcm001-0c"
           "splunk-scm001-0c"
           "splunk-scm002-0c"
           "splunk-scm003-0c")

HOSTS="${HOST_LIST[@]]}"

# Can use inventory scripts to pull hosts.  Example below is for aws.
# HOSTS=$(python ../../src/inventory/aws/get_inv.py --name-query splunk-* --add-quotes)

function appetite_call {
    # $1 -> param config
    appetite_cmd="python ../../src/appetite.py --num-conns 10 --config-file ../configs/demo_splunk/$1.conf --hosts ${HOST_LIST[@]]}"
    echo ${appetite_cmd}
    ${appetite_cmd}
}

function run_appetite {
    # Run set of appetite commands
    appetite_call "base_apps"

    appetite_call "apps"

    appetite_call "deployment_apps"
}

run_appetite

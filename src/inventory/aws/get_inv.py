#!/usr/bin/env python
# pylint: disable=no-member,missing-type-doc,missing-returns-doc,invalid-name
"""Script will get host ip and format based on hostname filter and parameters
"""
import sys
import re
import argparse
import boto3


def get_instance_info(region, tag, name_filter):
    """Get information about instances.

    Returns:
        Get instances based on name filter
    """

    ec2 = boto3.resource('ec2', region_name=region)

    ec2_filter = [{'Name': 'instance-state-name', 'Values': ['running']}]

    if name_filter:
        ec2_filter.append({'Name': 'tag:%s' % tag, 'Values': [name_filter]})

    instances_found = list(ec2.instances.filter(Filters=ec2_filter).all())
    try:
        if len(instances_found) < 1:
            return []

        return [{'name': next((tag['Value'] for tag in inst_info.tags if tag['Key'] == 'Name'), ""),
                 'instance': inst_info
                 } for inst_info in instances_found]
    except Exception as e: # pylint: disable=bare-except
        print "Instances %s do not exist." % name_filter
        print e.message
        sys.exit(1)


def add_quotes(input_str, is_quotes_added):
    """add quotes to incoming str

    Returns:
        Quotes added based on bool value
    """

    return '"%s"' % input_str if is_quotes_added else input_str


def parse_args():
    """Parse args

    :return: args
    """
    parser = argparse.ArgumentParser(
        description='Params for pulling aws instances for appetite')

    parser.add_argument("-n", "--name-query", help="filter on name based on aws tag",
                        dest="name_query")
    parser.add_argument("-x", "--regex", help="Secondary regex used for instance filtering",
                        dest="regex_filter", default="(.*?)")
    parser.add_argument("-r", "--region", help="region to query", default="us-west-2")
    parser.add_argument("-q", "--add-quotes", help="If quotes are added to output", action='store_true',
                        default=False, dest="add_quotes")
    parser.add_argument("-i", "--just-ips", help="get just the ips", action='store_true',
                        default=False, dest="just_ip")
    parser.add_argument("-t", "--tag", help="Tag to query",
                        dest="tag", default="Name")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    instances_info = get_instance_info(args.region, args.tag, args.name_query)

    for inst in instances_info:
        instance = inst['instance']

        if re.search(args.regex_filter, inst['name']):
            if args.just_ip:
                output_str = "%s" % instance.private_ip_address
            else:
                output_str = "%s:%s" % (inst['name'].split('.')[0], instance.private_ip_address)
            print '"%s"' % output_str if args.add_quotes else output_str

#!/usr/bin/env python
# pylint: disable=no-member,missing-type-doc,missing-returns-doc,invalid-name
"""Script will get host ip and format based on hostname filter and parameters
"""
import sys
import re
import argparse
from boto import ec2


def get_instance_info(region, name_filter, regex_filter):
    """Get information about instances.

    Returns:
        Get instances based on name filter
    """

    conn = ec2.connect_to_region(region)
    reservations = conn.get_all_instances(filters=name_filter)
    try:
        instances_found = [inst_i for res in reservations for inst_i in res.instances]
        if len(instances_found) < 1:
            return []

        unique_ami_ids = list(set([inst_j.image_id for inst_j in instances_found]))
        instance_users = {ami_id.id: 'centos' if ami_id.description and 'centos' in ami_id.description.lower()
                                     else 'ec2-user' for ami_id in conn.get_all_images(image_ids=unique_ami_ids)}
        instances = []
        for inst_info in instances_found:
            if inst_info.state == 'running' and re.search(regex_filter, inst_info.tags['Name']):
                instances.append({'instance': inst_info, 'user': instance_users[inst_info.image_id]})
    except Exception as e: # pylint: disable=bare-except
        print "Instances %s do not exist." % name_filter
        print e.message
        sys.exit(1)

    return instances


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
                        required=True, dest="name_query")
    parser.add_argument("-x", "--regex", help="Secondary regex used for instance filtering",
                        dest="regex_filter", default="(.*?)")
    parser.add_argument("-r", "--region", help="region to query", default="us-west-2")
    parser.add_argument("-q", "--add-quotes", help="If quotes are added to output", action='store_true',
                        default=False, dest="add_quotes")
    parser.add_argument("-i", "--just-ips", help="get just the ips", action='store_true',
                        default=False, dest="just_ip")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    instances_info = get_instance_info(args.region, {'tag:Name': args.name_query}, args.regex_filter)

    for inst in instances_info:
        instance = inst['instance']
        if args.just_ip:
            output_str = "%s" % instance.private_ip_address
        else:
            output_str = "%s:%s" % (instance.tags['Name'].split('.')[0], instance.private_ip_address)
        print '"%s"' % output_str if args.add_quotes else output_str

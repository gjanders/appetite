#!/usr/bin/python
#pylint: disable=relative-import,too-many-nested-blocks
"""Args used for configuring Appetite

This creates two methods for entering params.  The command line uses the
params defined in this file.  If a param file is included in the
command line, it will use the values in the file and overwrite any defined
and/or default files in the args.

Structure was created to allow multiple config files in the future, combining
multiple runs.
"""

import sys
import consts
import helpers

ARGS_PARAMS = []


def add_arg(*args, **kvargs):
    """Stored values for command line or config file"""

    # Create clean params, this is used for reference in args file
    params = [arg[2:] for arg in args if arg.startswith("--")]
    ARGS_PARAMS.append({"params": params, "args": args, "kvargs": kvargs})


def load_args(args_file):
    """Load args from file

    Pulls params from file
    """

    config = helpers.get_config(args_file)
    sections = config.sections()

    args_dict = {}

    for section in sections:
        options = config.options(section)

        # Look for params stanza
        if section.lower() == 'params':
            for i in range(0, len(ARGS_PARAMS)):
                app_arg = ARGS_PARAMS[i]
                for option in options:
                    # Check if param is within the config file
                    keyvalue = app_arg["kvargs"]
                    if option in app_arg['params']:
                        # Param are sometimes renamed for internal code use
                        opt_name = keyvalue['dest'] if 'dest' in keyvalue else option
                        # Basic logic to eval types
                        if isinstance(keyvalue["default"], bool):
                            args_dict[opt_name] = config.getboolean(section, option)
                        elif isinstance(keyvalue["default"], int):
                            args_dict[opt_name] = config.getint(section, option)
                        else:
                            args_dict[opt_name] = config.get(section, option).strip("'\"")

    return args_dict


def args_check(args):
    """Function to check if arg params are valid"""

    if not args.hosts:
        print "--hosts needs to be defined"
        sys.exit(1)

    if not args.app_binary or not args.app_folder:
        print "--app-binary or --app-folder needs to be defined"
        print args
        sys.exit(1)

    if not args.dryrun:
        # If key is not defined, can still run but no ssh connections
        # all ssh connections will go to dry run mode
        if len(args.ssh_keyfile) < 1:
            print "--ssh-keyfile file is not defined: %s" % args.ssh_keyfile

        if len(args.repo_url) < 1:
            print "--repo-url needed"
            sys.exit(1)

# Load in config file that can over write cmd args
add_arg('--config-file', metavar='cf',
        default=None, dest='config_file',
        help='config file used to in place of params')

add_arg('--commands-conf', metavar='cd',
        default=None, dest='command_conf',
        help='Location of the command.conf file.')

# Params needed for appetite to work
add_arg('--hosts', metavar='c', nargs='*', type=str,
        help='hosts to filter')

add_arg('--host-classes', metavar='hc', nargs='*', type=str,
        default=[], dest="host_classes",
        help='classes used to filter hosts')

add_arg('--boot-order', metavar='boot', nargs='*', type=str,
        default=[], dest="boot_order",
        help='Order which classes are booted.')

add_arg('--tmp-folder', metavar='dir', type=str,
        default="tmp", dest="tmp_folder",
        help='Folder where host apps and tars are created')

add_arg('--scratch-dir', metavar='dir', type=str,
        default="appetite_tmp", dest="scratch_dir",
        help='Location where repo and tmp folder is created')

add_arg('--apps-folder', metavar='f', type=str,
        default="base_apps", dest="apps_folder",
        help='location of applications for deployment '
             'relative to repo location')

add_arg('--apps-manifest', metavar='m', type=str,
        default="manifest_baseapps.csv", dest="apps_manifest",
        help='location of manifest located in the '
             'config folder in the repo')

add_arg('--repo-url', metavar='repourl', type=str,
        default="", dest="repo_url",
        help='Repo url location')

add_arg('--repo-branch', metavar='repobranch', type=str,
        default='master', dest="repo_branch",
        help='Repo branch')

add_arg('--ref-name', metavar='p', dest="refname", type=str,
        default='repo',
        help='Repo location and reference name'
             'used to tag apps.')

add_arg('--template-files', metavar='f', nargs='*', type=str,
        default=None, dest="template_files",
        help='templating key value files'
             '(*.json and/or *.ymal)')

add_arg('--template-filtering', metavar='f', type=str,
        default=None, dest="template_filtering",
        help='filter templated values using a external function.'
             'format => script_location:class.function'
             'format => script_location:function')

add_arg('--template-json', metavar='v', type=str,
        default=None, dest="template_json",
        help='templated values entered via json object through'
             'command line.')

add_arg('--name-formatting',
        metavar="pre{{appclass}}{{'%03d'%num}}{{site}}post",
        type=str, dest="name_formatting",
        default="spl{{appclass}}{{'%03d'%num}}-{{site}}test",
        help='Jinja2 name formatting of host names.'
             'This is used to determine pre and post fix')

add_arg('--app-folder', metavar='folder', type=str,
        default=None, dest="app_folder",
        help='Folder where application is installed'
             'on remote host')

add_arg('--app-binary', metavar='binary', type=str,
        default=None, dest="app_binary",
        help='Based on the app-folder on remote host,'
             'relative location of application binary')

add_arg('--logging-path', metavar='p', dest="logging_path",
        type=str, default=consts.LOGPATH,
        help='Logging path, logging has to be enabled for logs'
             'to be generated')

add_arg('-l', '--ssh-user', metavar='u', type=str,
        dest="ssh_user", default='ssh_user',
        help='The ssh user')

add_arg('-i', '--ssh-keyfile', metavar='f', type=str,
        dest="ssh_keyfile", default="",
        help='Path to ssh keyfile')

add_arg('-p', '--ssh-port', metavar='p', type=int,
        dest="ssh_port", default=22,
        help='ssh port')

add_arg('--num-conns', metavar='t', type=int,
        dest="num_connections",
        default=consts.DEFAULT_THREAD_POOL_SIZE,
        help='Number of concurrent connections used')

add_arg('-d', '--debug', action='store_true',
        default=False,
        help='Turns on debugging output')

add_arg('--disable-logging', action='store_true',
        default=False, dest="disable_logging",
        help='Log messages to file')

add_arg('-s', '--silent', action='store_true',
        default=False, dest="silent",
        help='Stop cmd output')

add_arg('--templating', action='store_true',
        default=False, dest="templating",
        help='Sets if templating is to be used.')

add_arg('--firstrun', action='store_true',
        default=False, dest="firstrun",
        help='States if the apps is being added are'
             'for first run.')

add_arg('--skip-repo-trigger', action='store_true',
        default=False, dest="skip_repo_sync",
        help='Skips repo trigger so that appetite always'
             'compares manifests.  Used for testing code all'
             'the way though.')

add_arg('-c', '--clean', action='store_true',
        default=False,
        help='Delete temp directories')

add_arg('--clean-repo', action='store_true',
        default=False, dest="clean_repo",
        help='Remove repo which will force a repo pull')

add_arg('--clean-metas', action='store_true',
        default=False, dest="clean_metas",
        help='Remove metas forcing a re-download when'
             'initializing')

add_arg('--build-test-apps', action='store_true',
        default=False, dest="build_test_apps",
        help='Build test app directories')

add_arg('--dry-run', action='store_true',
        default=False, dest="dryrun",
        help='Runs in a none connected mode for testing')

add_arg('--no-strict-commitids', action='store_false',
        default=True, dest="strict_commitids",
        help='Fail if commit ids are not being used.'
             'If false will use the last commit id')

add_arg('--install-ignore', metavar='t', type=str,
        default=None, dest="install_ignore",
        help='Global install ignore check and remove '
             'files/folders in every app.')

add_arg('--site-override', metavar='t', type=str,
        default=False, dest="site_override",
        help='By default all updates will be done a '
             'single site at a time in boot-order. '
             'This will override that setting and '
             'Update all host within a boot-order')

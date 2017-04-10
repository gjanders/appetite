#!/usr/bin/env python
# pylint: disable=too-complex,no-name-in-module,import-error,relative-import,missing-returns-doc,too-many-instance-attributes,too-many-branches,too-many-statements,too-many-arguments,too-many-locals,no-member,invalid-name
"""Appetite Main.

Parent appetite class
"""

import os
import sys
import traceback
import csv
import shutil
import tarfile
import json
import time
from distutils.dir_util import copy_tree
from multiprocessing import Pool
import argparse

import modules.logger as Logger
import modules.consts as Consts
import modules.conn_manager as ConnManager
import modules.app_versioning as AppVersioning
import modules.helpers as Helpers
import modules.appetite_args as AppetiteArgs
from modules.appetite_core import AppetiteHosts, AppetiteHost
from modules.repo_manager import RepoManager
from modules.deployment_methods import DeploymentMethodsManager


def parse_args():
    """Parse args from the command line

    :return: args
    """
    parser = argparse.ArgumentParser(
        description='Deploy apps based on the manifest')

    for arg in AppetiteArgs.ARGS_PARAMS:
        parser.add_argument(*arg['args'], **arg['kvargs'])

    return parser.parse_args()


class Appetite(object):
    """Main appetite class"""

    # Stores and manages host and their applications
    appetite_hosts = AppetiteHosts()

    def __init__(self, is_already_running):
        self.args = parse_args()

        # default path for configs
        self.app_config_dir = os.path.abspath("../config")

        # Update args from config file
        if self.args.config_file:
            abs_config_file = os.path.abspath(os.path.dirname(
                self.args.config_file))
            self.args.__dict__.update(
                AppetiteArgs.load_args(self.args.config_file))
            self.app_config_dir = abs_config_file

        self.app_commands_file = os.path.join(
            self.app_config_dir, "commands.conf")

        if self.args.command_conf:
            self.app_commands_file = os.path.join(os.path.abspath(
                os.path.expandvars(self.args.command_conf)))

        AppetiteArgs.args_check(self.args)

        # Set up logging after args are set
        Logger.setup_logging('appetite_%s' % self.args.refname,
                             self.args.refname,
                             True, self.args.disable_logging,
                             self.args.silent,
                             self.args.logging_path)

        if is_already_running:
            Logger.info("Appetite is already processing")
            self.print_track_info(False, Helpers.get_track())
            return

        # Get host classes for filtering
        self.host_classes = self.args.host_classes.split(" ") \
            if isinstance(self.args.host_classes, basestring) \
            else self.args.host_classes

        # Reverse sorting needed for name filtering
        self.host_classes.sort(reverse=True)

        # Get boot ordering
        self.boot_ordering = Helpers.get_enchanced_boot_order(
            self.args.boot_order, self.host_classes)

        self.repo_name = self.args.repo_url.split('/')[-1].split('.')[0]
        self.scratch_location = os.path.join(os.path.abspath(
            os.path.expandvars(self.args.scratch_dir)), self.args.refname)
        self.repo_path = os.path.join(self.scratch_location, self.repo_name)
        self.apps_folder = os.path.join(self.repo_path, self.args.apps_folder)
        self.manifest_path = os.path.join(
            self.repo_path, Consts.CONFIG_PATH_NAME, self.args.apps_manifest)
        self.tmp_folder = os.path.join(self.scratch_location, self.args.tmp_folder)
        self.meta_folder = os.path.join(self.scratch_location, 'meta')
        self.tars_folder = os.path.join(self.tmp_folder, 'tars')
        self.hosts_folder = os.path.join(self.tmp_folder, 'hosts')
        self.remote_apps_path = os.path.normpath(self.args.app_folder)
        self.base_location, self.base_name = os.path.split(self.remote_apps_path)
        self.name_formatting = self.args.name_formatting.strip('"\'')
        self.meta_name = "%s%s" % (Consts.APPS_METADATE_FILENAME, self.args.refname)
        self.meta_remote_folder = os.path.join(self.remote_apps_path, Consts.META_DIR)
        self.meta_remote_logs_folder = os.path.join(
            self.meta_remote_folder, Consts.HOST_LOGS_FOLDER_NAME)
        self.meta_remote_file = "%s.json" % os.path.join(self.meta_remote_folder, self.meta_name)

        if self.args.clean:
            Helpers.delete_path(self.scratch_location)

        self.repo_manager = RepoManager(self.repo_name,
                                        self.args.repo_url,
                                        self.args.repo_branch,
                                        "",
                                        self.scratch_location,
                                        self.args.apps_manifest,
                                        self.args.dryrun)

        Logger.debug_on(self.args.debug)

        if not self.args.tmp_folder:
            Logger.errorout("tmp folder must be defined")

        # Deleting the tmp folder to keep installs clean
        Helpers.delete_path(self.tmp_folder)

        self.template_values = {}

        try:
            if self.args.template_files:
                template_paths = self.args.template_files

                # Incase one long string is entered
                if isinstance(self.args.template_files, basestring):
                    template_paths = self.args.template_files.split(' ')

                self.template_values = Helpers.load_templating(template_paths)
        except Exception as exception:
            Logger.errorout("No templating problem: %s" % exception.message)

        if self.args.template_json:
            try:
                self.template_values.update(json.loads(self.args.template_json.replace('\\"', '"')))
            except Exception as err:
                Logger.errorout("Error parsing --template-json", error=err.message)

        if self.args.template_filtering:
            self.template_values = Helpers.filter_object(self.template_values, self.args.template_filtering)

        ConnManager.set_globals(self.args.ssh_user,
                                self.args.ssh_keyfile,
                                self.args.ssh_port,
                                self.args.app_folder,
                                self.args.app_binary,
                                self.args.dryrun)

        self.ssh_app_commands = ConnManager.SshAppCommands(
            self.app_commands_file, self.template_values)

        # Load any files reference to appetite scripts folder before this
        # Working directories change with repo management
        repo_status = self.repo_manager.pull_repo(self.args.clean_repo)

        if not self.args.dryrun and repo_status < 0:
            Logger.errorout('Repo Error, Look at logs for details')

        repo_check_status = self.repo_manager.check_for_update()

        Logger.add_track_info(self.repo_manager.track)

        triggered = repo_check_status['triggered'] or repo_status == 1

        Logger.info('Repo pull', output=repo_check_status['output'], triggered=triggered)

        if not self.args.dryrun and not self.args.skip_repo_sync and not triggered:
            Logger.info('No repo update found', complete=False)
            self.print_track_info(False)
            sys.exit(0)

        self.repo_manager.set_commit_id()

        # Load in deploymentmethods.conf
        self.deployment_manager = DeploymentMethodsManager(self.repo_name, "",
                                                           self.scratch_location)

        # Generate hosts
        if self.args.hosts:
            # Incase one long string is entered
            if len(self.args.hosts) == 1:
                self.args.hosts = self.args.hosts[0].split(' ')

            for host in self.args.hosts:
                split_hostname = host.strip("'\"").split(':')
                clean_hostname = split_hostname[0].split('.')[0].strip("'\"")

                # With user name, the ssh hostname can be defined.  This allows
                # for IP addresses to be defined incase there is no DNS.
                host_data = Helpers.pull_class_from_host(
                    self.name_formatting, clean_hostname, self.host_classes)

                if host_data:
                    # Can use a specified hostname/IP.
                    # Default is the given hostname
                    ssh_host = split_hostname[len(split_hostname) - 1]
                    self.appetite_hosts.add_host(self, clean_hostname, host_data, ssh_host)
        else:
            # Create hosts based on classes
            for host_class in self.host_classes:
                self.appetite_hosts.add_host(self, Helpers.build_hostname(self.name_formatting,  # pylint: disable=no-value-for-parameter
                                                                          host_class,
                                                                          1))

        if self.appetite_hosts.is_empty():
            Logger.errorout("No hosts found after filtering")

        if self.args.clean_metas:
            Helpers.delete_path(self.meta_folder)

        # Only update if a manifest file is not found
        self.update_manifests(check_if_exists=True)

        Logger.info("appetite started", use_templating=self.args.templating,
                    firstrun=self.args.firstrun)

        self.populate_apps_to_hosts()

        changes_found = self.create_host_directories_and_tar()

        if changes_found:
            Logger.info("Start host updates")

            self.update_hosts()

            Logger.info("End host updates")

        self.print_track_info(changes_found)
        Logger.info("Appetite complete", complete=True, changes=changes_found)

    def populate_apps_to_hosts(self):
        """Parses the manifest and adds apps to hosts

        :return: None
        """
        Helpers.check_file(self.manifest_path)

        with open(self.manifest_path, 'rU') as csvfile:
            mreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            first_row = True
            # Go though each app
            for row in mreader:
                # Remove header if it exists
                if first_row:
                    # Defines column headers in manifest
                    column_headers = {col_name: -1
                                      for col_name in
                                      Consts.DEFAULT_COLUMN_HEADER}

                    # Get indexes for headers from the first row
                    num_columns = len(row)
                    for k in column_headers:
                        value_index = next((index for index in range(0, num_columns)
                                            if row[index].lower() == k), -1)
                        if value_index < 0:
                            Logger.errorout("Manifest header is missing", header=k)
                        column_headers[k] = value_index

                    first_row = False
                    continue

                if len(row) > 1:
                    row_values = Helpers.create_obj({
                        "commit_id": row[column_headers['commitid']],
                        "app_clean": self.deployment_manager.name_filter.sub("", row[
                            column_headers['application']]),
                        "app": row[column_headers['application']],
                        "deployment": row[column_headers['deploymentmethod']],
                        "white_list": row[column_headers['whitelist']].split(','),
                        "black_list": row[column_headers['blacklist']].split(',')
                    })

                    app_folder = os.path.join(self.apps_folder, row_values.app)

                    if self.args.build_test_apps:
                        # for testing - create test folders for apps
                        if not os.path.exists(app_folder):
                            Helpers.create_path(os.path.join(app_folder, "folder"), True)
                            app_test_file = "%s/%s.txt" % (app_folder, row_values.app_clean)
                            with open(app_test_file, 'wb') as touch:
                                touch.write("")

                    # Go through each host and see
                    # if the app is needed for the host
                    for host in self.appetite_hosts:
                        hostname = host.hostname
                        self.add_host(host, hostname, row_values, None, False)
                        self.bootstrap_firstrun_hosts(host, hostname, row_values)

            if self.appetite_hosts.is_empty():
                Logger.errorout("Manifest misconfiguration, "
                                "no apps for any hosts")

    def bootstrap_firstrun_hosts(self, host, hostname, row_values):
        """Function used to bootstrap apps on the first fun"""

        # Only run if the manifest is not found on the host (new app instance)
        if self.args.firstrun and not host.manifest_found:
            first_run = next((su_bootstrap for su_bootstrap in
                              self.deployment_manager.startup_bootstrap if
                              su_bootstrap['ref_class'] == host.app_class and
                              Helpers.check_name_formatting(
                                  self.name_formatting, hostname)), None)
            host.restart = True
            if first_run:
                # For the special case when instance is new,
                # #start up apps have to be included
                if first_run['update_method'] == row_values.deployment:
                    built_hostname = Helpers.build_hostname(self.name_formatting,
                                                            first_run['app_class'], 1)
                    self.add_host(host, built_hostname, row_values,
                                  first_run['ref_method'],
                                  True)

    def add_host(self, host, hostname, row_values, deployment, is_firstrun):
        """Add app to host"""

        if Helpers.check_host(hostname,
                              row_values.black_list,
                              row_values.white_list):
            host.add_app(self.args.refname,
                         AppetiteHost.create_app(
                             self.repo_manager,
                             self.deployment_manager,
                             row_values.app,
                             row_values.app_clean,
                             deployment if deployment else row_values.deployment,
                             row_values.commit_id,
                             hostname,
                             is_firstrun))

    def create_host_directories_and_tar(self):
        """Main packaging function

        Works in 3 parts:
          1. Validate app data and configurations
          2. Create tmp directories for each host with loaded apps and manifest
          3. Package (tar) up host tmp directories for distribution
        """

        Helpers.delete_path(self.tmp_folder)
        Helpers.create_path(self.tars_folder, True)

        self.repo_manager.set_commit_id()
        master_commit_log = self.repo_manager.get_commit_log()

        errors_found = False
        changes_found = False

        for host in self.appetite_hosts:  # pylint: disable=too-many-nested-blocks
            # Per host build apps folder and tar up based on class
            hostname = host.hostname
            apps = host.get_apps(self.args.refname)
            tarname = host.tarname

            apps = sorted(apps, key=lambda app: app.commit_id)

            tmp_hostname_dir = os.path.join(self.hosts_folder, hostname)
            tmp_hostname_meta = os.path.join(tmp_hostname_dir, Consts.META_DIR)

            apps_meta = []

            if len(apps) < 1:
                Logger.warn("Host with no apps", hostname=hostname)
                continue
            # Parse the remote meta file from the host
            # This file might not exist
            remote_meta_file = host.local_meta_file
            remote_metas_loaded = False
            if os.path.exists(remote_meta_file):
                try:
                    with open(remote_meta_file) as remote_data_file:
                        remote_metas_master = json.load(remote_data_file)
                        remote_metas_content = remote_metas_master['content'] \
                            if 'content' in remote_metas_master else remote_metas_master
                        remote_metas = [
                            AppetiteHost.create_app_from_object(self.repo_manager,
                                                                self.deployment_manager,
                                                                meta_data)
                            for meta_data in remote_metas_content]

                        remote_metas_loaded = True
                except Exception as exception:
                    Logger.error("Problems loading meta file",
                                 error=exception.message,
                                 path=remote_meta_file)
            elif not self.args.dryrun:
                Logger.warn("Local version of remote meta not found", file=remote_meta_file)

            ordered_unique_apps = sorted(list(set(apps)), key=lambda single_app:
            (single_app.name,
             single_app.commit_id,
             single_app.method_name))

            for iapp in ordered_unique_apps:
                app_occurrences = apps.count(iapp)
                if app_occurrences > 1:
                    Logger.warn("Dup app found", host=host.hostname,
                                app_info=iapp.app_key,
                                occurences=app_occurrences)

            # Validate app data and configurations

            # Go through the apps and checks to see if there are any errors
            # This is where the remote meta is compared to the newly generated
            # lists of apps from the manifest
            for app in apps:
                raw_app_path = os.path.join(self.apps_folder, app.name)

                # Check the commit Id for problems
                if app.commit_id:
                    self.repo_manager.set_commit_id(app.commit_id)
                else:  # pylint: disable=else-if-used
                    if self.args.strict_commitids:
                        Logger.error("Application with missing commit Id", hostname=hostname,
                                     app=app.name)
                        errors_found = True
                        continue
                    else:
                        app._commit_id = master_commit_log['app_commit_id']  # pylint: disable=protected-access
                        self.repo_manager.set_commit_id(app.commit_id)

                # Checks if app listed in the manifest
                # exists with the correct commit id
                if Helpers.check_path(raw_app_path):
                    meta_to_append = None
                    app.refresh_version_info(self.args.refname, Consts.META_APP_UNCHANGED)
                    remote_meta = None

                    # Check to see what has changed
                    if remote_metas_loaded:
                        # Searches remote meta to see if application already exists
                        remote_meta = next((rmeta for rmeta in remote_metas
                                            if app.check_names(rmeta)), None)

                        if remote_meta:
                            # If app does exist on system, have the commit ids changed
                            if remote_meta.commit_id != app.commit_id:
                                meta_to_append = app.set_status_changed()
                            else:
                                # meta has not changed so use existing meta
                                meta_to_append = app.clone
                                meta_to_append.update_app_version(app)

                            # to track is a app is removed it is removed from the remote meta
                            remote_metas.remove(remote_meta)

                    if not meta_to_append:
                        # There is no remote meta so all files should be added
                        meta_to_append = app.set_status_added()

                    if remote_meta and meta_to_append:
                        Logger.debug("Check meta logic",
                                     outcome=Helpers.debug_app_versions(meta_to_append,
                                                                        remote_meta,
                                                                        meta_to_append.status))
                    apps_meta.append(meta_to_append)
                else:
                    Logger.error("Missing application",
                                 hostname=hostname,
                                 app=app.name,
                                 path=raw_app_path)
                    continue

            if remote_metas_loaded and len(remote_metas) > 0:
                # Any apps left in the remote meta do not exist in the current
                # manifest and should be deleted
                delete_list = []
                for deleted_app in remote_metas:
                    if deleted_app.method_info:
                        deleted_app.set_status_deleted()
                        # Added logic check to catch method changes
                        added_app_found = next((app for app in apps_meta
                                                if app.status == Consts.META_APP_ADDED
                                                and app.name == deleted_app.name and
                                                app.method_info['path'] ==
                                                deleted_app.method_info['path']), None)
                        if added_app_found:
                            added_app_found.set_status_changed()
                        else:
                            delete_list.append(deleted_app)
                    else:
                        Logger.error(
                            "Problems with method info for deleted app.",
                            hostname=hostname, app=deleted_app.name)

                apps_meta += delete_list

            # Only do something if there has been a change
            if len([app for app in apps_meta if not app.is_unchanged]) < 1:
                continue

            # No point continuing if there is no connection to the host
            if not self.check_host_connection(host):
                continue

            # Clean command lines for auth params
            # This data is ingested so creds should be removed
            # apps_meta = [updated_app.clone for updated_app in apps_meta]

            if not self.args.disable_logging:
                for updated_app in apps_meta:
                    Logger.log_event(updated_app.to_dict)

            # Applications that actually needs to be updated
            tar_apps = sorted([updated_app for updated_app in apps_meta if updated_app.updated],
                              key=lambda tar_app: tar_app.app)

            use_templating = self.template_values and self.args.templating

            # Checking will allow templating otherwise will skip steps
            Helpers.create_path(os.path.join(tmp_hostname_meta, Consts.HOST_LOGS_FOLDER_NAME), True)
            if len(tar_apps) > 0:
                # All error checks have been done above, build out
                # the hosts directory and tar up
                for updated_app in tar_apps:
                    app_path = os.path.join(tmp_hostname_dir, updated_app.method_info['path'])
                    Helpers.create_path(app_path, True)
                    raw_app_path = os.path.join(self.apps_folder, updated_app.name)

                    self.repo_manager.set_commit_id(updated_app.commit_id)

                    if updated_app.update_method_is_copy:
                        app_dest = os.path.join(app_path, updated_app.app_clean)
                    else:
                        app_dest = app_path

                    copy_tree(raw_app_path, app_dest)

                    lookups_inclusion_location = os.path.join(app_dest,
                                                              self.deployment_manager.
                                                              inclusion_filename)

                    ignore_dir = os.path.join(app_dest, Consts.TMP_IGNORE_DIR)

                    # Ignore files/folders set in the global configurations
                    if self.args.install_ignore:
                        content_ignored_results = Helpers.move_regexed_files(self.args.install_ignore.split(';'),
                                                                             app_dest,
                                                                             ignore_dir)
                        files_included = content_ignored_results['files_moved']

                        if len(files_included) > 0:
                            Logger.error("Globally these files should not exist in the App. "
                                         "The files have been removed from the install.",
                                         files=files_included,
                                         hostname=hostname,
                                         app=updated_app.name)

                        # Users should not have the capability to include files from the
                        # global ignore.
                        Helpers.delete_path(ignore_dir)

                    # Defined folders/files are to move out of application.
                    # This is defined in the deploymentmethods.conf
                    # If an app is installed for the first time, all files should be included
                    if 'install_ignore' in updated_app.method_info and not updated_app.is_added:
                        Helpers.move_regexed_files(updated_app.method_info['install_ignore'],
                                                   app_dest,
                                                   ignore_dir)

                        # If there is a inclusion file, include files back into app.
                        # This is defined on a per app basis
                        if os.path.isfile(lookups_inclusion_location):
                            with open(lookups_inclusion_location, "r") as f:
                                lines = [l.strip() for l in f.readlines()]

                            lookup_inclusion_results = Helpers.move_regexed_files(lines,
                                                                                  ignore_dir,
                                                                                  app_dest)

                            if lookup_inclusion_results['errors_found']:
                                Logger.error("Lookup inclusion error found",
                                             paths=lookup_inclusion_results['path_errors'],
                                             hostname=hostname,
                                             app=updated_app.name)
                                # Problem with host inclusion,
                                # move to next host
                                continue

                            updated_app.method_info['inclusions'] = \
                                lookup_inclusion_results['filed_moved']

                            # Update objects with inclusions
                            updated_app.copy_value_to_method_info('inclusions', apps_meta)
                            os.remove(lookups_inclusion_location)

                    Helpers.delete_path(ignore_dir)

                    if use_templating and not updated_app.method_info['skip_templating']:
                        # Can template based on vars from templated
                        # values, hosts vars and app vars
                        Helpers.template_directory(app_dest,
                                                   [self.template_values,
                                                    host.to_dict,
                                                    updated_app.to_dict])

                    # Should only change access and create version file if a whole app is copied
                    if updated_app.update_method_is_copy:
                        for host_path, host_dir, host_files in os.walk(app_dest):  # pylint: disable=unused-variable
                            for host_file in host_files:
                                # Splunk apps can have active binaries in multiple languages
                                # This is a catch all to make sure apps have all the required
                                # permissions.
                                chmod = 0755
                                os.chmod(os.path.join(host_path, host_file), chmod)

                        with open(os.path.join(app_dest, Helpers.get_app_version_filename()), "w") as f:
                            f.write(updated_app.to_json)

                        AppVersioning.create_app_version(app_dest,
                                                         updated_app.
                                                         commit_log['app_abbrev_commit_id'])

            apps_distro = Helpers.content_wrapper(apps_meta,
                                                  Consts.META_CURRENT,
                                                  hostname,
                                                  self.track)

            # Meta file used as source of truth on instance
            master_meta = self.create_meta_files(tmp_hostname_meta, '', apps_distro)

            # check be used to update and test manifest changes locally
            if self.args.dryrun:
                Helpers.create_path(host.local_meta_file)
                shutil.copy(master_meta, host.local_meta_file)

            # Always want clean logs ingested
            selected_apps = Helpers.select_and_update_apps(apps_meta,
                                                           Consts.META_CURRENT,
                                                           False)

            self.create_meta_log(tmp_hostname_meta, '', selected_apps, Helpers.get_utc())

            host.updates = Helpers.content_process(apps_meta,
                                                   Consts.META_UPDATED,
                                                   hostname,
                                                   self.track,
                                                   True)

            # Create the meta change file
            self.create_meta_files(tmp_hostname_meta,
                                   '_update',
                                   Helpers.content_convert(host.updates))

            # Clean updates file for logging
            selected_apps = Helpers.select_and_update_apps(apps_meta,
                                                           Consts.META_UPDATED,
                                                           True)

            self.create_meta_log(tmp_hostname_meta, '_update', selected_apps, Helpers.get_utc())

            Logger.info("Changes found", updates=Helpers.content_wrapper(apps_meta,
                                                                         Consts.META_UPDATED,
                                                                         hostname,
                                                                         self.track,
                                                                         True))

            # Package (tar) up host tmp directories for distribution
            tar = tarfile.open(os.path.join(self.tars_folder, "%s.tar.gz" % tarname), "w:gz")
            tar.add(tmp_hostname_dir, arcname=os.path.basename(self.base_name))
            tar.close()

            changes_found = True

        if errors_found:
            sys.exit(1)

        self.repo_manager.set_commit_id()

        return changes_found

    @property
    def track(self):
        """Reference to Track info

        The track info contains the uuid, datatime and commit id of the current job
        """
        return self.repo_manager.track

    def print_track_info(self, changed, track=None):
        """Pretty print track info"""
        ref_track = track if track else self.track

        ref_track['changed'] = changed
        print(json.dumps(ref_track, sort_keys=True, indent=4,
                         separators=(',', ': ')))

    def update_manifests(self, hosts=None, check_if_exists=False):
        """Loads local manifest

        Tries to get the remote manifest from the host
        """

        if not hosts:
            hosts = self.appetite_hosts.hosts

        if isinstance(hosts, AppetiteHost):
            hosts = [hosts]

        results = self._thread_hosts('update_manifest', hosts, check_if_exists)

        # Since threading does not share variables, the results are copied back into the
        # host objects
        if results:
            for i, host in enumerate(hosts):
                if not host.from_dict(results[i]):
                    Logger.warn("Threading host mismatch")

    def update_manifest(self, host, check_if_exists=False):
        """Loads local manifest for a host for local host"""

        host.manifest_found = os.path.isfile(host.local_meta_file)
        if not check_if_exists or not host.manifest_found:
            if self.check_host_connection(host):
                host.manifest_found = ConnManager.get_json_file(host, self.meta_remote_file,
                                                                host.local_meta_file, True)
        return host.get_threaded_values

    def create_meta_filename(self, host_meta_path, postfix, extension, timestamp=None):
        """create file name for the meta content"""

        if timestamp:
            filtered_timestamp = Helpers.filter_timestamp(timestamp)
            return "%s%s_%s.%s" % (os.path.join(host_meta_path,
                                                Consts.HOST_LOGS_FOLDER_NAME,
                                                self.meta_name),
                                   postfix, filtered_timestamp, extension)
        else:
            return "%s%s.%s" % (os.path.join(host_meta_path,
                                             host_meta_path,
                                             self.meta_name),
                                postfix, extension)

    def create_meta_files(self, host_meta_path, postfix, content, timestamp=None):
        """Creates a meta json file

        Create a single json file with a host meta object
        """

        created_meta = self.create_meta_filename(host_meta_path, postfix, 'json', timestamp)
        with open(created_meta, "w") as f:
            if timestamp:
                f.write(json.dumps(content))
            else:
                f.write(json.dumps(content, sort_keys=True, indent=4, separators=(',', ': ')))
        return created_meta

    def create_meta_log(self, host_meta_path, postfix, content, timestamp=None):
        """Creates a meta json log file

        Create file with multiple entries for content.
        This is used for logging
        """

        created_meta_log = self.create_meta_filename(host_meta_path, postfix, 'log', timestamp)
        with open(created_meta_log, "a") as f:
            for entry in content:
                f.write("%s\n" % entry.to_json)
        return created_meta_log

    def update_hosts(self):
        """Update each host

        Installs apps and run commands to each host.
        """

        # When running check, no connections to host will be used
        changed_hosts = [host for host in self.appetite_hosts if host.updates]

        # Lists Sites
        host_sites = list(set([host.site for host in self.appetite_hosts]))
        host_sites.sort()

        # Organize scripts to run in order
        for script_seq in Consts.DM_COMMANDS_SEQUENCE:
            for boot_group in self.boot_ordering:
                host_group = [host for host in changed_hosts if host.app_class in boot_group]

                # If site override is enabled then do all hosts
                if self.args.site_override:
                    if len(host_group) > 0:
                        Logger.info("Starting script run hosts", site='all', boot_group=boot_group,
                                    script_level=script_seq)
                        self._thread_hosts('update_host', host_group, script_seq)
                    continue

                # By default will use sites to break up installs
                for host_site in host_sites:
                    host_site_group = [host for host in host_group if host.site == host_site]
                    if len(host_site_group) > 0:
                        Logger.info("Starting script run hosts", site=str(host_site), boot_group=boot_group,
                                    script_level=script_seq)
                        self._thread_hosts('update_host', host_site_group, script_seq)

    def _thread_hosts(self, update_funct, hosts, *args):
        """Helper function to set up threading for hosts"""

        # If single thread/host is used, no threading is needed
        if self.args.num_connections == 1 or len(hosts) < 2:
            for host in hosts:
                Helpers.call_func((self, update_funct, host) + args)
            return

        host_pool = Pool(processes=self.args.num_connections)
        iter_hosts = [(self, update_funct, host) + args for host in hosts]
        results = host_pool.map(Helpers.call_func, iter_hosts)
        host_pool.close()
        host_pool.join()

        return results

    @staticmethod
    def check_host_connection(host):
        """Checks to see if appetite can connect to the host"""
        if host.can_connect is None:
            host.can_connect = ConnManager.check_connection(host)

            if not host.can_connect:
                Logger.error("Can not connect to host",
                             host=host.hostname)
        return host.can_connect

    def update_host(self, host, update_method):
        """Update function for host

        Separate function used to update a single host
        """

        if not self.check_host_connection(host):
            return

        commands = []

        # Run commands if specified
        if len(host.updates[update_method]) > 0:
            commands = self.ssh_app_commands.enhance_commands(
                host.updates[update_method], [self.template_values, host.to_dict])

        not_update_command = update_method != Consts.DM_COMMANDS_SEQUENCE[1]

        self.run_commands(commands, host, not_update_command, True)

        # If just running a script, should ignore all function related to app deployment
        if not_update_command:
            return

        apps = host.updates['content']

        # Delete apps
        deleted_apps = list(set([app.path(self.args.app_folder) for app in apps if
                                 app.method_info['delete_first'] or
                                 app.status == Consts.META_APP_DELETED]))

        for delete_app in deleted_apps:
            ConnManager.delete(host, delete_app, True)

        # Clear old version files
        changed_apps = list(set([app.path(self.args.app_folder) for app in apps if
                                 app.status == Consts.META_APP_CHANGED]))

        for changed_app in changed_apps:
            ConnManager.clear_files(host, changed_app,
                                    "%s*" % Consts.VERSIONS_FILENAME, True)

        # Install apps and new manifests
        ConnManager.untar(host, self.base_location, True)

        # In case the command already has a restart in it
        restart_notfound = next((False for command in commands if command['command'].name == "restart"), True)

        # Restart App if needed
        if (host.updates["restart"] or host.restart) and restart_notfound:
            commands.append(self.ssh_app_commands.enhance_commands(
                [ConnManager.COMMAND_RESTART_NAME], [self.template_values,
                                                     host.to_dict])[0])

        self.run_commands(commands, host)

        # Get latest manifest since host has been updated
        self.update_manifest(host)

        # Clean up old manifest files
        ConnManager.rotate_logs(host, self.meta_remote_logs_folder,
                                Consts.DEFAULT_LOG_RETENTION)

    def run_commands(self, commands, host, run_commands=False, pre_install=False):
        """Run listed commands"""

        for command in commands:
            command_object = command['command']
            if run_commands or command_object.pre_install == pre_install:
                if not self.args.dryrun and self.ssh_app_commands.run_command(command, host)\
                        and command_object.delay > 0:
                    time.sleep(command_object.delay)


def call_func(args):
    """Call a class function with a single param"""
    args['func_ref'](args['host'])


def main():
    # Makes sure there is only one instance of this script running
    with Helpers.RunSingleInstance() as is_running:
        try:
            Appetite(is_running)
        except Exception as e:
            trace_list = traceback.format_exc().split('\n')
            Logger.exception("Catch all", e, err_message=e.message, trace=trace_list)
            sys.exit(1)


if __name__ == "__main__":
    main()

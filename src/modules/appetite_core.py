#!/usr/bin/env python
#pylint: disable=relative-import,too-many-instance-attributes,too-many-public-methods,undefined-variable,attribute-defined-outside-init
"""Appetite Core

Classes and functions to support the storage and conversion of applications
and hosts.
"""

import sys
import os
import traceback
import json
import logger
import consts
import helpers
import deployment_methods


class AppetiteHosts(object):
    """Class to store a working list of hosts"""
    hosts = []
    meta_info = {"host_groups": {"app_class": {}, "all": [], "ref": {}}}

    def add_host(self, _source, _hostname, host_data, _ssh_hostname=None, _tarname=None):
        """Add host to list"""
        host_classes = self.meta_info["host_groups"]["app_class"]
        host_all = self.meta_info["host_groups"]["all"]
        host_ref = self.meta_info["host_groups"]["ref"]
        if next((False for host in self.hosts if host.hostname == _hostname), True):
            app_host = AppetiteHost(_source, _hostname, host_data, _ssh_hostname, _tarname)
            self.hosts.append(app_host)

            # Create vars used for templating cmd
            if app_host.app_class not in host_classes:
                host_classes[app_host.app_class] = []
            host_classes[app_host.app_class].append(app_host.hostname)
            host_all.append(app_host.hostname)
            host_ref[app_host.hostname] = app_host.ssh_hostname

    def is_empty(self):
        """Host empty check"""
        return len(self.hosts) < 1

    def __iter__(self):
        for host in self.hosts:
            yield host

    def build_meta(self, template_values):
        host_classes = self.meta_info["host_groups"]["app_class"]
        host_all = self.meta_info["host_groups"]["all"]

        for appclass in host_classes:
            sorted(appclass)

        sorted(host_all)

        return helpers.merge_templates([template_values, self.meta_info])


class AppetiteHost(object):
    """Class to store a host object

       Stores values attributed to a host and a list of applications based on
       source types.
    """

    def __init__(self, _source, _hostname, host_data, _ssh_hostname, _tarname):
        """Init of a host object"""
        self.hostname = _hostname
        self.app_class = "N/A"
        #self.app_class = host_data[consts.NAME_FORMATTING[0]['name']]
        #self.site = host_data[consts.NAME_FORMATTING[1]['name']]
        self.site = "1"
        #self.host_index = host_data[consts.NAME_FORMATTING[1]['name']]
        self.host_index = 001
        self.tarname = _tarname if _tarname else _hostname
        self.ssh_hostname = _ssh_hostname if _ssh_hostname else _hostname
        self.local_meta_file = os.path.join(_source.meta_folder,
                                            _hostname,
                                            consts.META_DIR,
                                            "%s.json" % _source.meta_name)
        self.tar_file = os.path.join(_source.tars_folder, "%s.tar.gz" % self.tarname)
        self.manifest_found = False
        self.restart = False
        self.can_connect = None
        self.bootstrap = False

        self.updates = None

        self._app_sources = {}

    @staticmethod
    def create_app(_repo_mng, _deployment_mng, app, app_clean, deployment, app_commit_id, hostname,
                   _is_firstrun):
        """Create new application from param"""
        app_obj = AppetiteApp(_repo_mng, _deployment_mng, app, app_clean,
                              deployment, app_commit_id, hostname, _is_firstrun)
        return app_obj

    @staticmethod
    def create_app_from_object(_repo_mng, _deployment_mng, obj):
        """Create new application from object"""
        app_obj = AppetiteApp(_repo_mng, _deployment_mng, obj)
        return app_obj

    @property
    def to_dict(self):
        """Convert application to to dict"""
        return helpers.create_dict(self.__dict__)

    @property
    def get_threaded_values(self):
        """Get values that would change during multithreading"""
        return {'hostname': self.hostname, 'can_connect': self.can_connect, 'manifest_found': self.manifest_found}

    def from_dict(self, dict_in):
        """Load values in from dictionary"""
        if self.hostname != dict_in['hostname']:
            return False

        for key, value in dict_in.items():
            self.__dict__[key] = value

        return True

    def add_app(self, source, app):
        """Add application based on source"""
        if source not in self._app_sources:
            self._app_sources[source] = []

        self._app_sources[source].append(app)

    def get_apps(self, source):
        """Get application based on soutce"""
        if source not in self._app_sources:
            return []
        return self._app_sources[source]


class AppetiteApp(object):
    """Class to store a application object

       Stores values attributed to a application
    """

    def __init__(self, _repo_mng, _deployment_mng, *args):
        """Init of a application object"""
        self.__repo_mng = _repo_mng
        self.__deployment_mng = _deployment_mng

        num_args = len(args)

        self.commit_log = None
        self.content_type = helpers.get_update_str(False)
        self.repo_source = None

        if num_args > 0:
            if num_args == 1:
                self.from_object(args[0])
            else:
                self.from_params(*args)

    def from_params(self, _app, _app_clean, _method, _commit_id, _hostname, _is_firstrun=False):
        """populate application from params"""

        self._deployment_method = self.__deployment_mng.get_deployment_method(_method)

        if not self._deployment_method:
            logger.errorout("Deployment method for app invalid", app=_app,
                            method=_method)

        self.app = _app
        self.app_clean = _app_clean
        self.source_hostname = _hostname
        self.method_info = self._deployment_method.data.copy()
        self._commit_id = None if _commit_id == 'N/A' or len(_commit_id) == 0 else _commit_id
        self.is_firstrun = _is_firstrun
        self.track = self.__repo_mng.track
        self.status = consts.META_APP_UNCHANGED
        self.updated = False
        self.app_creation_datetime = helpers.get_utc()
        self.content_type = helpers.get_update_str(False)

        return self

    def from_object(self, obj):
        """Populate application from object"""
        loaded_obj = obj

        if isinstance(obj, str):
            try:
                loaded_obj = json.loads(obj)
            except Exception as exception:
                logger.exception("Problem loading json apps object", exception,
                                 err_message=exception.message,
                                 trace=json.dumps(traceback.format_exc()))
                sys.exit(1)

        for key, value in loaded_obj.items():
            self.__dict__[key] = value

        if self.commit_log:
            for key, value in consts.RENAME_COMMIT_LOG_KEYS.items():
                if key in self.commit_log:
                    self.commit_log[value] = self.commit_log.pop(key, None)

        return self

    def update_content_type(self, isupdate):
        """Change content type flag to updated or list"""
        self.content_type = helpers.get_update_str(isupdate)

    @property
    def to_dict(self):
        """Convert application into dict"""
        return helpers.create_dict(self.__dict__)

    @property
    def to_json(self):
        """Convert application into json"""
        std_values = self.to_dict
        return json.dumps(std_values)

    @property
    def clone(self):
        """Clone current application object"""
        cloned = AppetiteApp(self.__repo_mng, self.__deployment_mng)
        cloned.from_object(self.to_json)

        return cloned

    @property
    def commit_id(self):
        """Get the app source commit id"""
        if self.commit_log:
            return self.commit_log['app_commit_id']

        return self._commit_id if self._commit_id else ""

    @property
    def name(self):
        """Get the name of the application"""
        return self.app

    @property
    def method_name(self):
        """Get the install method used for the application"""
        return self.method_info['name']

    @property
    def update_method_is_copy(self):
        """Check if the app is just going to be copied

        This is the same as NOT copy_in_place
        """
        return self.method_info['update_method'] == deployment_methods.CP_METHOD_COPY

    def path(self, app_path):
        """Path where application is going to be copied"""
        return os.path.join(app_path, self.method_info['path'], self.app_clean)

    @property
    def summary(self):
        """Create summery of app data"""
        return {
            'app': self.app,
            'app_commit_id': self.commit_id,
            'method_name': self.method_name,
            'status': self.status,
            'hostname': self.source_hostname}

    @property
    def is_unchanged(self):
        """If the app is unchanged"""
        return self.status == consts.META_APP_UNCHANGED

    def set_status_unchanged(self):
        """Set app to unchanged

        This status is set when reading older manfest files that had a change.
        """
        return self.reset_app_version_status(consts.META_APP_UNCHANGED)

    @property
    def is_added(self):
        """Check to see if the application is newly added"""
        return self.status == consts.META_APP_ADDED

    def set_status_added(self):
        """Sets status to added

        Previous value typically unchanged.
        """
        return self.reset_app_version_status(consts.META_APP_ADDED)

    @property
    def is_deleted(self):
        """Checks to see if an app is deleted"""
        return self.status == consts.META_APP_DELETED

    def set_status_deleted(self):
        """Set status of app to deleted.

        Typically happens when the manifest is missing an app.
        """
        return self.reset_app_version_status(consts.META_APP_DELETED)

    @property
    def is_changed(self):
        """Checks to see if the app is changed"""
        return self.status == consts.META_APP_CHANGED

    def set_status_changed(self):
        """Set the app status to changed

        If an app changes commit ids this is typically set
        """
        return self.reset_app_version_status(consts.META_APP_CHANGED)

    @property
    def currently_installed(self):
        """Checks to see if the app is currently installed

        This checks if the status is added, changed or unchanged
        """
        return self.status in consts.META_CURRENT

    @property
    def has_been_updated(self):
        """Checks to see if the app has been updated

        This checks if the status is added, changed or deleted
        """
        return self.status in consts.META_UPDATED

    @property
    def has_changed(self):
        """Checks to see if the app has been changed

        This checks if the status is added or changed
        """
        return self.status in consts.META_CHANGED

    def reset_app_version_status(self, status):
        """Reset Status of app after it is unchanged or deleted"""

        self.status = status
        self.updated = self.has_changed
        if 'commands' not in self.method_info:
            self.method_info['commands'] = []

        return self

    def refresh_version_info(self, repo_source, status):
        """Information about the application used for versioning"""

        self.commit_log = self.__repo_mng.get_commit_log()
        self.repo_source = repo_source

        self.reset_app_version_status(status)

        return self

    def __eq__(self, other):
        """Operator =="""
        if not self.check_names(other):
            return False

        if other.commit_id != self.commit_id:
            return False

        return True

    @property
    def app_key(self):
        """App key to define uniqueness of app"""
        return {
            "app": self.app,
            "commit_id": self.commit_id,
            "method_name": self.method_name
        }

    def __hash__(self):
        """Create unique hash based on app key"""
        return hash(tuple([self.app_key[key] for key in self.app_key]))

    def check_names(self, other):
        """Check to see if app name and method match"""
        if other.app != self.app:
            return False

        if other.method_name != self.method_name:
            return False

        return True

    def update_app_version(self, other_app):
        """"Makes sure app version meta is always updated.
        Helps maintain method_info and future proof version structures.
        """

        if self == other_app:
            version_num = other_app.track['version']

            self.app_creation_datetime = other_app.app_creation_datetime

            if 'inclusions' in self.method_info:
                self.method_info['inclusions'] = \
                    other_app.method_info['inclusions']

            # Object updated to newest meta object
            self.track['version'] = version_num

        return self

    def copy_value_to_method_info(self, value, *argv):
        """Copy a key value into param objects"""

        if value not in self.method_info:
            return

        for arg in argv:
            app_list = arg['content'] if 'content' in arg else arg

            app_content = next((app_content for app_content in app_list
                                if app_content.app == self.app), None)
            if app_content:
                self.method_info[value] = app_content.method_info[value]

#!/usr/bin/python
#pylint: disable=too-complex,relative-import,invalid-name,too-many-branches,too-many-instance-attributes
"""DeploymentMethods

Manages data into and out of the deploymentmethods.conf file.
"""

import re
import os

import logger
import consts
import helpers

CP_METHOD_COPY = 'copy'
CP_METHOD_COPY_IN_PLACE = 'copy_in_place'

UPDATE_METHODS = [CP_METHOD_COPY_IN_PLACE, CP_METHOD_COPY]

DM_MANDATORY_KEYS = ['path', 'update_method']
DM_BOOL_KEYS = ['delete_first', 'all_sites', 'restart', 'skip_templating']

DM_STARTUP_PREFIX = 'StartupBootstrap_'


class SingleDeploymentMethod(object):
    """Class stores vars needed for a single deployment"""
    def __init__(self, _config, section, skip_check=False):
        """Init stores vars from a configuration file"""
        options = self.section_data = _config.options(section)

        self.data = {'name': section}

        for seq in consts.DM_COMMANDS_SEQUENCE:
            self.data[seq] = []

        # Checks to make sure all mandatory keys are present
        if not skip_check:
            check_options = list(set(DM_MANDATORY_KEYS) - set(options))
            if len(check_options) > 0:
                logger.errorout("key not found in deployment methods",
                                name=section, options=options)

            for bool_key in DM_BOOL_KEYS:
                self.data[bool_key] = False

        self.data['install_ignore'] = ""

        # Load vars from configuration file
        for option in options:
            try:
                if option in DM_BOOL_KEYS:
                    self.data[option] = _config.getboolean(section, option)
                else:
                    config_option = _config.get(section, option).strip('"\'')
                    if 'command' in option:
                        self.data[consts.DM_COMMANDS_SEQUENCE[1]].append(config_option)
                    elif 'script' in option:
                        if len(self.data[consts.DM_COMMANDS_SEQUENCE[1]]) < 1:
                            self.data[consts.DM_COMMANDS_SEQUENCE[0]].append(config_option)
                        else:
                            self.data[consts.DM_COMMANDS_SEQUENCE[2]].append(config_option)
                    elif 'install_ignore' in option:
                        self.data[option] = config_option.split(';')
                    elif 'update_method' in option:
                        self.data[option] = config_option
                        # Checking to see if update methods exist
                        if config_option in UPDATE_METHODS or section.startswith(DM_STARTUP_PREFIX):
                            self.data[option] = config_option
                        else:
                            logger.errorout("Update method does not exist",
                                            method_used=section,
                                            app=config_option)
                    else:
                        self.data[option] = config_option
            except Exception as e:
                logger.errorout("Problem getting option from deployment methods",
                                name=section, option=option, error=e.message)

    @property
    def name(self):
        return self.data['name']


class DeploymentMethodsManager(object):
    """Class to manage list of deployments"""

    def __init__(self, _reponame, _repo_path, _scratch_folder):
        """Init of deployment methods manager"""
        self.paths = {
            'scratch_path': _scratch_folder,
            'absolute_path': os.path.join(_scratch_folder, _repo_path)
        }

        self.paths['repo_path'] = os.path.join(self.paths['absolute_path'],
                                               _reponame)
        self.paths['dm_filepath'] = os.path.join(self.paths['repo_path'],
                                                 consts.CONFIG_PATH_NAME,
                                                 consts.DEPLOYMENT_METHODS_FILENAME)

        self.deployment_methods = []
        self.boot_order = []
        self.startup_bootstrap = []
        self.default_setting = {}
        self.name_filter = None
        self.inclusion_filename = ""

        # set xform for config otherwise text will be normalized to lowercase
        self.config = helpers.get_config(self.paths['dm_filepath'])
        self.load_config()

    def load_config(self):
        """Loads deployment methods configuration"""

        sections = self.config.sections()

        for section in sections:
            if section.lower() == 'default':
                self.default_setting = SingleDeploymentMethod(self.config, section, True)
                self.name_filter = re.compile(self.default_setting.data['app_name_filter'])
                self.inclusion_filename = self.default_setting.data['install_inclusion_file']
            elif section.startswith(DM_STARTUP_PREFIX):
                su_bootstrap = SingleDeploymentMethod(self.config, section, True).data
                self.startup_bootstrap.append(su_bootstrap)
            else:
                self.deployment_methods.append(SingleDeploymentMethod(self.config, section))

    def get_deployment_method(self, deployment_method_name):
        """Get deployment methods based on names"""

        return next((dm for dm in self.deployment_methods if dm.name == deployment_method_name),
                    None)

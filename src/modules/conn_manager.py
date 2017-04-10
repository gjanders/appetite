#!/usr/bin/env python
# pylint: disable=too-complex,relative-import,no-member,invalid-name,too-many-arguments,import-error
"""Command Manger

Module to handle ssh communication.  Commands are either dictated though
functions or restricted configuration files.
"""

import os
import json
import time
import paramiko
from scp import SCPClient

import consts
import logger
import helpers

# Creating global object to share
CREDS = helpers.create_obj(
    {
        "SSH_USER": "",
        "SSH_KEYFILE": "",
        "APP_DIR": "",
        "APP_BIN": "",
        "DRY_RUN": False,
        "PK": ""
    }
)

COMMAND_CLASS_NAME = 'limit_to_hosts'
COMMAND_RESTART_NAME = 'restart'
COMMAND_MODULE_INIT = 'initization'
COMMAND_MODULE_CUSTOM = 'custom_command'
COMMAND_MODULE_BUILTIN = 'buildin_function'

# Used to check configuration for mandatory stanzas
MANDATORY_COMMAND_STANZAS = [
    COMMAND_RESTART_NAME
]

# Retry limits
MAX_SSH_RETRIES = 3
MAX_SCP_RETRIES = 4
SESSION_TIMEOUT = 30
CONNECTION_TIMEOUT = 10

# Filtering for error ssh messasge.
ERROR_MESSAGES = [
    'No such file or directory',
    'Permission denied',
    'No such file'
]


def set_globals(user, keyfile, port, app_dir, app_bin, dry_run=False):
    """Set global vars"""

    CREDS.SSH_USER = user
    CREDS.SSH_KEYFILE = os.path.expanduser(keyfile)
    CREDS.SSH_PORT = port
    CREDS.PK = None
    CREDS.APP_DIR = app_dir
    CREDS.APP_BIN = app_bin
    CREDS.DRY_RUN = dry_run

    if len(keyfile) < 1 or len(CREDS.SSH_USER) < 1:
        CREDS.DRY_RUN = True
    else:
        CREDS.PK = paramiko.RSAKey.from_private_key_file(CREDS.SSH_KEYFILE)


class SshAppCommand(object): # pylint: disable=too-many-instance-attributes
    """Class to store single stored command"""

    user = None
    password = None

    def __init__(self, config, name, options, render_funct, index=-1):
        """Init single ssh command"""

        self.limit_to_hosts = []
        self.suppress_limit_to_hosts_warnings = False
        self.use_auth = False
        self.name = name
        self.cmd = None
        self.use_root = False
        self.use_app_binary = True
        self.pre_install = False
        self.index = index
        self.delay = consts.REMOTE_CMD_RUN_SLEEP_TIMER

        for option in options:
            try:
                config_option = config.get(name, option).strip('"\'')
                if COMMAND_CLASS_NAME == option:
                    self.limit_to_hosts = json.loads(config_option)
                elif option == 'use_root':
                    self.use_root = config.getboolean(name, option)
                elif option == 'use_app_binary':
                    self.use_app_binary = config.getboolean(name, option)
                elif option == 'suppress_limit_to_hosts_warnings':
                    self.suppress_limit_to_hosts_warnings = config.getboolean(name, option)
                elif option == 'use_auth':
                    self.use_auth = config.getboolean(name, option)
                elif option == 'pre_install':
                    self.pre_install = config.getboolean(name, option)
                elif option == 'cmd':
                    self.cmd = render_funct(config_option)
                elif option == 'delay':
                    self.delay = int(config_option)
            except Exception as e:
                logger.errorout("Problem getting option from command conf",
                                name=name,
                                option=option,
                                module=COMMAND_MODULE_INIT,
                                error_msg=str(e))

    def can_host_use(self, host_class):
        """Checks if command can be used by hosr"""
        if len(self.limit_to_hosts) < 1:
            return True

        return host_class in self.limit_to_hosts


class SshAppCommands(object):
    """Class to run stored cmd commands

    Commands are loaded in from a file and stored for use.
    These commands are reference from the deploymentmethods.conf.
    """

    _commands = {}
    __auth = ""

    def __init__(self, commands_config, template_values):
        """Init Shh App Commands"""

        self.__auth = ""
        self.template_values = template_values

        # set xform for config otherwise text will be normalized to lowercase
        self.config = helpers.get_config(commands_config)
        self.load_commands()

    def load_commands(self):
        """Load restricted cmd command"""

        sections = self.config.sections()

        index = 0

        for section in sections:
            options = self.config.options(section)

            if section == 'auth':
                self.__auth = self.render_values(self.config.get(section, 'postfix'))
                continue

            self._commands[section] = SshAppCommand(self.config, section, options, self.render_values, index)
            index += 1

        if not set(MANDATORY_COMMAND_STANZAS) <= set(self._commands):
            logger.errorout("Missing command stanza",
                            needed=MANDATORY_COMMAND_STANZAS,
                            module=COMMAND_MODULE_INIT)

    def render_values(self, value):
        return helpers.render_template(value.strip('"\''), self.template_values)

    def find_commands(self, command_name):
        """Basic command to find command"""

        return self._commands[command_name] if command_name in self._commands \
            else None

    def enhance_commands(self, commands_list, templating_values):
        """Checks and enchances with known listed commands"""

        tvalues = helpers.merge_templates(templating_values)

        # preserve order while getting rid of dup entries
        unique_list = []
        [unique_list.append(single_command) for single_command in commands_list if single_command not in unique_list]  # pylint: disable=expression-not-assigned
        invalid_commands = [command for command in list(unique_list)
                            if command not in self._commands]

        if len(invalid_commands) > 0:
            logger.warning("Invalid command(s) found",
                           commands=invalid_commands,
                           module=COMMAND_MODULE_INIT)
            return []

        enhance_list = [self._commands[command] for command in unique_list]

        filtered_commands = [{"cmd": helpers.render_template(command.cmd, tvalues),
                              "command": command}
                             for command in enhance_list]

        return filtered_commands

    def get_cmd(self, ecommand, is_clean=False):
        """Generate cmd with full path"""

        app_cmd = ecommand['cmd']
        command = ecommand['command']

        # Can only use auth with app binary
        if command.use_app_binary:
            app_cmd = "%s %s" % (os.path.join(CREDS.APP_DIR, CREDS.APP_BIN), app_cmd)

        if not is_clean:
            if command.use_auth:
                app_cmd = "%s %s" % (app_cmd, self.__auth)

            if command.use_root:
                app_cmd = "sudo %s" % app_cmd

        return app_cmd

    def get_cmd_clean(self, ecommand):
        """Returns clean cmd command"""

        return self.get_cmd(ecommand, is_clean=True)

    def run_command(self, ecommand, host):
        """Run single stored command"""

        command = ecommand['command']

        # Check to see if host can run command
        if not command.can_host_use(host.app_class):
            if not command.suppress_limit_to_hosts_warnings:
                logger.warn("Invalid host for command",
                            command=command.name,
                            hostname=host.hostname,
                            module=COMMAND_MODULE_INIT,
                            allowed_hosts=command.limit_to_hosts)
            return False

        # Call root is already taken applied in get_cmd
        ssh_run = SshRun(host.hostname, host.ssh_hostname, "",
                         helpers.get_function_name(), False)

        logger.info("SSH Started",
                    state=0,
                    hostname=host.hostname,
                    command=command.name,
                    module=COMMAND_MODULE_CUSTOM)

        results = ssh_run.run_single(self.get_cmd(ecommand))

        ssh_run.close_ssh_channel()

        _log_rc(results,
                "SSH Finished",
                state=1,
                auth=command.use_auth,
                app_binary=command.use_app_binary,
                hostname=host.hostname,
                command=command.name,
                cmd=self.get_cmd_clean(ecommand),
                output=results,
                module=COMMAND_MODULE_CUSTOM)
        return True


class SshRun(object):
    """Class wraps ssh command to allow detailed logging and extendability"""

    def __init__(self, hostname, ssh_hostname, filepath, function_name, is_root):
        """Init for ssh run class"""

        self.ssh_hostname = ssh_hostname
        self.hostname = hostname
        self.filepath = filepath
        self.function_name = function_name
        self.is_root = is_root

        self.ssh = None

        self._ssh_cmds = []

    @staticmethod
    def get_ssh_client(hostname, ssh_hostname):
        """Tries to create ssh client

        Create ssh client based on the username and ssh key
        """

        if not CREDS.SSH_KEYFILE:
            logger.errorout("ssh_keyfile not set",
                            module=COMMAND_MODULE_CUSTOM)

        retries = 0

        while retries < MAX_SSH_RETRIES:
            try:
                ssh = paramiko.SSHClient()
                ssh.load_system_host_keys()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh.connect(hostname=ssh_hostname,
                            username=CREDS.SSH_USER,
                            port=CREDS.SSH_PORT,
                            pkey=CREDS.PK,
                            timeout=CONNECTION_TIMEOUT)

                return ssh
            except paramiko.BadAuthenticationType:
                logger.error("BadAuthenticationType",
                             hostname=hostname,
                             module=COMMAND_MODULE_CUSTOM)
                return
            except paramiko.AuthenticationException:
                logger.error("Authentication failed",
                             hostname=hostname,
                             module=COMMAND_MODULE_CUSTOM)
                return
            except paramiko.BadHostKeyException:
                logger.error("BadHostKeyException",
                             fix="Edit known_hosts file to remove the entry",
                             hostname=hostname,
                             module=COMMAND_MODULE_CUSTOM)
                return
            except paramiko.SSHException:
                logger.error("SSHException",
                             hostname=hostname,
                             module=COMMAND_MODULE_CUSTOM)
                return
            except Exception as e:
                if retries == 0:
                    logger.error("Problems connecting to host",
                                 hostname=hostname,
                                 module=COMMAND_MODULE_CUSTOM,
                                 error=e.message)
                retries += 1
                time.sleep(1)

        logger.error("Can not connect to host",
                     hostname=hostname,
                     module=COMMAND_MODULE_CUSTOM)

        return None

    def add_cmd(self, cmd):
        """Adds a single command to the list"""

        self._ssh_cmds.append(cmd)

    def create_ssh_channel(self):
        """Crete a ssh channel for running command"""

        if CREDS.DRY_RUN:
            return True

        if not self.ssh:
            self.ssh = SshRun.get_ssh_client(self.hostname, self.ssh_hostname)
        return self.ssh

    def close_ssh_channel(self):
        """Close ssh channel if already open"""

        if self.ssh and not CREDS.DRY_RUN:
            self.ssh.close()
            self.ssh = None

    def run(self):
        """Runs the list of commands in order

        This does not run a single session, each command is a seperate connection
        """

        outputs = []
        if not self.create_ssh_channel():
            return

        for cmd in self._ssh_cmds:
            outputs.append(self.run_single(cmd, self.ssh))

        self.close_ssh_channel()

        run_obj = {
            "rc": next((1 for output in outputs if output['rc'] > 0), 0),
            "outputs": outputs
        }

        return run_obj

    def _add_root(self, cmd):
        return "sudo %s" % cmd if self.is_root else cmd

    def run_single(self, cmd, ssh=None):
        """Runs a single cmd command on the remote host
        """

        if not ssh:
            if not self.create_ssh_channel():
                return {"rc": 1,
                        "stderror": "Error creating ssh channel",
                        "stdout": "",
                        "function": self.function_name}
            ssh = self.ssh

        rc = 0
        std_out = ""
        std_error = ""

        # Simple check on cmd to look for redirection
        helpers.cmd_check(cmd)

        if not CREDS.DRY_RUN:
            # Dangerous command, only use if commands are filtered/protected
            # Only command either defined here or in the command.conf should
            # run here.
            stdin, stdout, stderr = ssh.exec_command(self._add_root(cmd), get_pty=True, timeout=SESSION_TIMEOUT)  # nosec
            rc = stdout.channel.recv_exit_status()

            std_out = stdout.read()
            std_error = stderr.read()
            stdin.flush()

        return {"stdout": std_out,
                "stderror": std_error,
                "function": self.function_name,
                "rc": rc}


# Helper ssh function
def copy_to_host(host, remote_file, local_file, is_root=False):
    """Copy file to remote host

    Function first copies file to remote user directory and then moving.
    Final move depends to right to directory.
    """

    _lpath, lfilename = os.path.split(local_file)
    rpath, rfilename = os.path.split(remote_file)

    local_filepath = os.path.join('./', lfilename)

    if len(rfilename) < 1:
        rfilename = lfilename
        remote_file = os.path.join(rpath, rfilename)

    if not os.path.isfile(local_file):
        logger.error("File to copy does not exist",
                     file=local_file,
                     module=COMMAND_MODULE_CUSTOM)
        return False

    ssh_run = SshRun(host.hostname, host.ssh_hostname, local_file,
                     helpers.get_function_name(), is_root)

    if not ssh_run.create_ssh_channel():
        return False

    success = True

    if not CREDS.DRY_RUN:
        retries = 0
        success = False
        while retries < MAX_SCP_RETRIES:
            # Copies file to remote users directory
            with SCPClient(ssh_run.ssh.get_transport()) as scp:
                try:
                    scp.put(local_file, lfilename)
                    success = True
                    break
                except Exception as e:
                    if _error_check(e.message, remote_file, host.hostname,
                                    "copy_to_host"):
                        return
            retries += 1
            time.sleep(2)

    if not success:
        logger.error("Problem using scp",
                     hostname=host.hostname,
                     local_file=local_file,
                     module=COMMAND_MODULE_CUSTOM)
        return False

    if local_filepath != remote_file:
        # Only copy file if not the same location
        ssh_run.add_cmd("mkdir -p %s" % rpath)
        ssh_run.add_cmd("mv %s %s" % (lfilename, remote_file))

    if is_root:
        # Make sure root permission are set if needed
        ssh_run.add_cmd("chown root:root %s" % remote_file)
        ssh_run.add_cmd("restorecon %s" % remote_file)

    results = ssh_run.run()

    _log_rc(results,
            ssh_run.function_name,
            hostname=host.hostname,
            remote_file=remote_file,
            local_file=local_file,
            outputs=results['outputs'],
            module=COMMAND_MODULE_BUILTIN)

    return results['rc'] < 1


def untar(host, location, is_root):
    """Copy and untar file on remote host"""

    _path, tar = os.path.split(host.tar_file)
    func_name = helpers.get_function_name()
    outcome = {'rc': 1}
    tar_cmd = "tar -zxvf %s -C %s" % (tar, location)

    if copy_to_host(host, "./", host.tar_file, False):

        ssh_run = SshRun(host.hostname, host.ssh_hostname, host.tar_file, func_name, is_root)

        # Untar bundle
        ssh_run.add_cmd(tar_cmd)

        # Remove old tar file
        ssh_run.add_cmd("rm -rf ./%s" % tar)

        outcome = ssh_run.run()

    _log_rc(outcome,
            func_name,
            cmd=tar_cmd,
            hostname=host.hostname,
            content=outcome['outputs'][0]['stdout'].split('\r\n') if outcome['rc'] < 1 else "",
            location=location,
            module=COMMAND_MODULE_BUILTIN)

    return True


def delete(host, remote_object, is_root=False, app_path_check=True):
    """Delete file/folder on remote host

    Function limits deleting to only files in the application directory
    """

    if not check_path(remote_object, app_path_check):
        return False

    results = run_cmd(host, "rm -rf %s" % remote_object, remote_object,
                      helpers.get_function_name(), is_root)

    return results['rc'] < 1


def check_connection(host):
    """Check to see if the connection to the host is valid"""

    results = run_cmd(host, "echo checking_connection")

    return results['rc'] < 1


def rotate_logs(host, log_path, retention, is_root=False):
    """Function to rotate appetite logs"""

    if not check_path(log_path):
        return False

    results = run_cmd(host, "find %s -type f -mtime +%d -delete" % (log_path, retention),
                      helpers.get_function_name(), log_path, is_root)

    return results['rc'] < 1


def clear_files(host, app_path, file_regex, is_root=False):
    """Removes files from server"""

    if not check_path(app_path):
        return False

    results = run_cmd(host, "rm -f %s " % os.path.join(app_path, file_regex),
                      helpers.get_function_name(), app_path, is_root)

    return results['rc'] < 1


def get_file_content(host, remote_file, local_file, is_root=False):
    """Get content of file from remote host"""

    helpers.create_path(local_file)

    return run_cmd(host, "cat %s" % remote_file,
                   helpers.get_function_name(), remote_file, is_root, False)


def get_json_file(host, remote_file, local_file, is_root=False):
    """Get json file from remote host"""

    if CREDS.DRY_RUN:
        return False

    file_content = get_file_content(host, remote_file, local_file, is_root)

    if file_content['rc'] > 0:
        return False

    if not CREDS.DRY_RUN:
        try:
            json.loads(file_content['stdout'])
        except ValueError as e:
            if _error_check(e.message, remote_file, host.hostname,
                            "get_json_file"):
                return False

        with open(local_file, 'w') as f:
            f.write(file_content['stdout'])

    return True


def run_cmd(host, cmd, path="", func_name=None, is_root=False, show_stdout=True):
    """Generic function to run single commands"""

    func_name = func_name if func_name else helpers.get_function_name()
    ssh_run = SshRun(host.hostname, host.ssh_hostname, path,
                     func_name, is_root)

    output = ssh_run.run_single(cmd)

    ssh_run.close_ssh_channel()

    # Clear stdout if needed
    updated_output = output
    if not show_stdout:
        updated_output = output.copy()
        updated_output['stdout'] = ""

    _log_rc(output,
            ssh_run.function_name,
            hostname=host.hostname,
            cmd=cmd,
            module=COMMAND_MODULE_BUILTIN,
            output=updated_output
            )

    return output


def check_path(remote_object, app_path_check=True):
    """Check if path is with in application directory"""

    # Should only be allow to delete things the app directory
    if app_path_check:
        if not remote_object.startswith(CREDS.APP_DIR):
            logger.warn("Can only delete files with in the app dir",
                        path=remote_object,
                        module=COMMAND_MODULE_CUSTOM,
                        path_check=app_path_check)
            return False
    return True


# Helper error checking
def _error_check(err_msg, remote_file, hostname, function_name):
    """Generic error checker for communication"""

    if len(err_msg) > 0:
        error_msg = next((err for err in ERROR_MESSAGES if err in err_msg), "Communication Error")

        logger.error(error_msg,
                     function=function_name,
                     filename=remote_file,
                     hostname=hostname,
                     module=COMMAND_MODULE_CUSTOM)


def _log_rc(cmd_output, funct_name, **kvarg):
    """Generic logger that picks correct log type based on return code"""

    rc = cmd_output['rc'] if 'rc' in cmd_output else cmd_output

    logger.log(logger.decide_level(rc),
               funct_name,
               **kvarg
               )

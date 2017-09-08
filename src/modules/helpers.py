#!/usr/bin/python
#pylint: disable=relative-import,invalid-name,missing-returns-doc
"""Basic helper functions and classes
"""

import os
import uuid
import datetime
import re
import imp
import json
import traceback
import shlex
import shutil
import ConfigParser
import fcntl
from subprocess import Popen, STDOUT, PIPE # nosec
from jinja2 import Environment, FileSystemLoader, Template, meta
import yaml

import consts
import logger
import version

DM_FILTER_COMMANDS = re.compile(r"-auth.* ", re.IGNORECASE)
REDIRECT_COMMANDS = ['&&', '&', '>', '1>', '2>', '>>', '1>>', '2>>', '<', '&>', '|', "||"]
REMOVE_LAST_FOLDER = re.compile(r"[^/]+/?$")
APPETITE_LOCKFILE = "appetite_lock"
LOCK_PATH = "/tmp/%s" % APPETITE_LOCKFILE # nosec


def create_path(path, is_dir=False):
    """Create Path"""
    try:
        split_path = path if is_dir else os.path.split(path)[0]
        if not os.path.exists(split_path):
            os.makedirs(split_path)
    except Exception as e:
        logger.exception("Problem creating folder", e, path=path)
        return False
    return True


def delete_path(path):
    """Delete path including content"""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception as e:
        logger.exception("Problem deleting folder", e, path=path)
        return False
    return True


def check_path(path, file_name=None):
    """Check path to see if it has the correct permissions to write"""
    if not os.path.exists(path):
        return False

    if os.access(path, os.W_OK) and os.access(path, os.R_OK):
        if file_name:
            try:
                open(os.path.join(path, file_name), 'w')
            except OSError:
                return False
        return True
    return False


def check_file(filepath):
    """Check is file exists"""
    if not os.path.isfile(filepath):
        logger.errorout("Can not find file", path=filepath)

    return True


def get_uid():
    """Generate a uid string"""
    return str(uuid.uuid1())


def get_track():
    """Get track information

    The track is a object tagged to all events and applications.  It helps
    identify objects and track deployments
    """
    return {"uid": get_uid(),
            "push_commit_id": "",
            "push_abbrev_commit_id": "",
            "process_datetime": get_utc(),
            "version": version.APPETITE_VERSION}


def get_utc():
    """Basic function to get Datetime in Zulu"""
    return "%sZ" % (datetime.datetime.utcnow().isoformat("T"))


def filter_content(content):
    """Filter content to make sure it can be built into json object
    """
    filtered_content = re.sub(r'[^\x00-\x7f]', r' ', content.strip("'").
                              replace("\n", "\\n").
                              replace("\r", "").
                              replace("\"", "'"))

    return filtered_content


def get_utc_filtered():
    """Filtered utc time

    This can be used within file name
    """
    return "%sZ" % filter_timestamp(datetime.datetime.utcnow().isoformat("T"))


def filter_timestamp(timestamp):
    """Filter timestamp for file creation"""
    return re.sub(r"[TZ\-:.]", "", timestamp)


def get_update_str(isupdate):
    """Gets correct tag for update and list

    This is used to tag the status of a whole manifest
    """
    return 'update' if isupdate else 'list'


def get_contents(filename):
    """Outputs lines (list) from file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return f.readlines()
    return None


def write_contents(filename, content):
    """Write content (list) to files"""
    create_path(filename)
    with open(filename, 'w') as f:
        f.writelines(content)


def get_template_content(path):
    """Read either yml or json files and store them as dict"""
    template_dict = {}

    _filename, file_extension = os.path.splitext(path)
    file_extension = file_extension.replace('.', '')
    if file_extension in consts.TEMPLATING_EXTS:
        try:
            template_content = {}
            abs_path = os.path.abspath(os.path.expandvars(path))
            with open(abs_path, 'r') as stream:
                if file_extension in consts.JSON_EXTS:
                    template_content = json.load(stream) #nosec
                elif file_extension in consts.YMAL_EXTS:
                    template_content = yaml.safe_load(stream) #nosec
            template_dict.update(template_content)
        except Exception as e:
            logger.errorout("Error reading templating file",
                            file=path, error=e.message)
    else:
        logger.errorout("No templating file found",
                        file=path)

    return template_dict


def filter_object(contents, filter_function):
    """Import module to filter contents of object """
    filter_funct = function_importer(filter_function)

    return _filter_content(filter_funct, contents) if filter_funct else contents


def _filter_content(filter_funct, contents):
    """Recursive function to filters child objects"""

    if isinstance(contents, dict):
        return {key: _filter_content(filter_funct, value) for key, value in contents.items()}
    if isinstance(contents, list):
        return [_filter_content(filter_funct, value) for value in contents]

    try:
        return filter_funct(contents)
    except Exception as e:
        print "Exception: %s" % e.message
        return None


def function_importer(mod_str): # pylint: disable=too-complex
    """Import Module from external source"""
    mod_split = mod_str.split(":")
    if len(mod_split) != 2:
        logger.error("Can not import function", mod=mod_str)
        return None

    mod_path = mod_split[0]
    funct_name = mod_split[1].split('.')

    path, filename = os.path.split(mod_path)
    mod_name, ext = os.path.splitext(filename) # pylint: disable=unused-variable
    mod = None

    # try to load precompiled in first if it exists
    if os.path.exists(os.path.join(path, mod_name)+'.pyc'):
        try:
            mod = imp.load_compiled(mod_name, mod_path)
        except: # pylint: disable=bare-except
            pass

    if os.path.exists(os.path.join(path, mod_name)+'.py'):
        try:
            mod = imp.load_source(mod_name, mod_path)
        except Exception as e:
            logger.error("No Class to import", mod=mod_str, error=e.message)

    # Pull function if embedded in classes
    for i, mod_part in enumerate(funct_name):
        if mod and hasattr(mod, mod_part):
            if i == len(funct_name) - 1:
                if len(funct_name) > 1:
                    return getattr(mod(), mod_part)
                return getattr(mod, mod_part)
            mod = getattr(mod, mod_part)

    logger.error("Function not valid/callable", mod=mod_str)
    return None


def create_obj(d):
    """Create an object from a dict"""
    return type('D', (object,), d)()


def create_dict(o):
    """Creates a dict from a object/class"""
    return dict((key, value) for key, value in o.items()
                if not callable(value) and not key.startswith('_'))


def get_function_name():
    """Get the calling function name"""
    return traceback.extract_stack(None, 2)[0][2]


def get_app_version_filename():
    """Create and object from a dict"""
    return "%s_%s%s" % (consts.VERSIONS_FILENAME, get_utc_filtered(), consts.VERSIONS_FILENAME_EXT)


def make_func_obj(func_ref, host):
    """Create function object to call in call func"""
    return {
        'func_ref': func_ref,
        'host': host
    }


def call_func(args):
    """Call a class function with a single param"""
    func = getattr(args[0], args[1])
    return func(*args[2:])


def load_templating(paths):
    """Load and merge files used for templating

    Multiple template files can be inputted to create a master template object
    """
    master_template = {}

    if isinstance(paths, basestring):
        paths = [paths]

    for path in paths:
        master_template.update(get_template_content(path))

    return master_template


def get_config(config_file):
    """Read and get a config object

    Reads and checks an external configuration file
    """

    config = ConfigParser.ConfigParser(allow_no_value=True)

    config_fullpath = os.path.abspath(os.path.expandvars(config_file))

    # set xform for config otherwise text will be normalized to lowercase
    config.optionxform = str

    if not os.path.isfile(config_fullpath):
        logger.errorout("Commands config file does not exist",
                        path=config_file)
    try:
        if not config.read(config_fullpath):
            logger.errorout("Problem reading command config file")
    except Exception as e:
        logger.errorout('Error reading command config',
                        path=config_file,
                        error=e.message)

    return config


def run(cmd, working_dir=None, dry_run=False):
    """Runs local cmd command"""

    cmd_split = shlex.split(cmd) if isinstance(cmd, basestring) else cmd

    if dry_run:
        return " ".join(cmd_split), 0

    try:
        p = Popen(cmd_split, shell=False, stderr=STDOUT, stdout=PIPE, cwd=working_dir)

        communicate = p.communicate()

        return communicate[0].strip(), p.returncode
    except OSError as e:
        logger.errorout("Run OSError", error=e.message)
    except: # pylint: disable=bare-except
        logger.errorout("Run Error")

    return


def cmd_check(cmd):
    """Basic check for redirection in command"""

    try:
        results = next((False for param in shlex.split(cmd)
                        for rparam in REDIRECT_COMMANDS
                        if rparam == param), True)

        if not results:
            logger.warning("Possible injection", cmd=cmd)
    except Exception as error:
        logger.warning("Possible injection/weirdness", cmd=cmd, error=error.message)


def check_host(hostname, black_list, white_list):
    """Check hostname to see if it valid

    Checks if the hostname is in the white and black list and return back
    according to the regex filtering.
    """

    for host_regex in black_list:
        if len(host_regex) > 1 and re.search(host_regex, hostname):
            return False

    for host_regex in white_list:
        if re.search(host_regex, hostname):
            return True

    return False


def split_naming(naming_format):
    """Gets the pre and post fix from the hostname"""

    return {'prefix': naming_format.split('{{')[0],
            'postfix': naming_format.split('}}')[-1]}


def check_name_formatting(naming_format, hostname):
    """Very basic check to see if the pre and postfix match"""
    naming_struct = split_naming(naming_format)

    return (hostname.endswith(naming_struct['postfix']) and
            hostname.startswith(naming_struct['prefix']))


def pull_class_from_host(naming_format, hostname, app_classes):
    """Pull the class from the host name based on the """

    host_data = pull_data_from_host(naming_format, hostname, {})

    # Check to see if the pre-post fixes are the same as the
    # naming formating
    if not check_name_formatting(naming_format, hostname):
        return None

    return next((host_data for app_class in app_classes if host_data[consts.NAME_FORMATTING[0]['name']] == app_class), None)


def pull_data_from_host(naming_format, hostname, already_found):
    """Pull the data from the host name based on the naming format"""

    fillers = {}

    value_to_parse = None
    for name_format in consts.NAME_FORMATTING:
        name = name_format['name']
        if name in already_found:
            fillers[name] = already_found[name]
            continue

        fillers[name] = 0
        if value_to_parse is None:
            fillers[name] = consts.NAME_FORMATTING_SPLIT_TOKEN
            value_to_parse = name_format

        if name_format['format_type'] == 'str':
            fillers[name] = str(fillers[name])

    if value_to_parse is None:
        return already_found

    str_w_token = render_template(naming_format, fillers)

    split_via_token = str_w_token.split(str(consts.NAME_FORMATTING_SPLIT_TOKEN))
    lower_index = len(split_via_token[0])
    data_len = len(hostname)-(lower_index + len(split_via_token[1]) if len(split_via_token) > 1 else 0)

    parsed_value = hostname[lower_index:][:data_len]

    if parsed_value.isdigit():
        parsed_value = int(parsed_value)

    already_found[value_to_parse['name']] = parsed_value

    return pull_data_from_host(naming_format, hostname, already_found)


def build_hostname(naming_format, s_class, host_num):
    """Build a hostname based on class and num given"""

    name = render_template(naming_format, {
        consts.NAME_FORMATTING[0]['name']: s_class,  # class
        consts.NAME_FORMATTING[1]['name']: "0",      # site
        consts.NAME_FORMATTING[2]['name']: host_num  # host index
    })

    if len(get_template_vars(name)) > 1:
        logger.errorout("Host name not templated correctly")

    return name


def get_enchanced_boot_order(boot_order, host_classes):
    """Get the boot order with all classes and structured for use

    The boot_order only shows strict hosts ordering, if any are
    missing they are added to the end of the list.

    Returns: [[host_classes]]
    """
    remaining_hosts = list(host_classes)
    eboot_order = []
    boot_order_list = boot_order.split(" ") if isinstance(boot_order, basestring) else boot_order

    for boot_group in boot_order_list:
        boot_group_list = boot_group.split(",")

        # After all defined host are removed, what is left
        # is put into the last array entry
        for boot_class in boot_group_list:
            if boot_class not in remaining_hosts:
                logger.warn("Boot Order class does not exists in host classes",
                            boot_class=boot_class)
                continue
            remaining_hosts.remove(boot_class)

        eboot_order.append(boot_group_list)
    eboot_order.append(remaining_hosts)

    return eboot_order


def update_content_type(contents, isupdate):
    """Update content type for all apps"""

    for content in contents:
        content.update_content_type(isupdate)

    return contents


def select_and_update_apps(apps_meta, status_types, isupdate):
    """Gets apps based on status types and update the content type
    (updated | list).
    """
    return update_content_type([updated_app for updated_app in apps_meta
                                if updated_app.status in status_types],
                               isupdate)


def debug_app_versions(a_version, b_version, outcome):
    """Create a debug object used for logging

    Audit trail created to show difference between apps being changed.
    """

    if a_version is None or b_version is None:
        print "version not found"

    app_versions = {
        'a': a_version.summary,
        'b': b_version.summary
    }

    if not a_version or not b_version:
        return {
            'outcome': outcome,
            'app_versions': app_versions
        }

    return {
        'check_app_and_method': a_version.check_names(b_version),
        'check_all': a_version == b_version,
        'outcome': outcome,
        'app_versions': app_versions
    }


def content_process(apps_meta, status_types, hostname, track, isupdate):
    """Process content so that source information is ready for distribution

    Host and application information is packaged into a single object.
    """

    if status_types:
        selected_apps = select_and_update_apps(apps_meta, status_types, isupdate)
    else:
        selected_apps = [updated_app for updated_app in apps_meta]

    contents = [updated_app for updated_app in selected_apps if not updated_app.is_firstrun]

    changed_content = [app for app in contents if not app.is_unchanged]

    contents = update_content_type(contents, isupdate)

    source = {
        'content': contents,
        'creation_datetime': get_utc(),
        'track': track,
        'source_hostname': hostname,
        'change_count': len(changed_content),
        'content_type': get_update_str(isupdate)
    }

    if isupdate:
        for seq in consts.DM_COMMANDS_SEQUENCE:
            # Preserve sequence order and remove dups
            source[seq] = []
            [source[seq].append(commands) for app in changed_content for commands in app.method_info[seq] if commands not in source[seq]]  # pylint: disable=expression-not-assigned
        source['restart'] = next((True for app in changed_content
                                  if app.method_info['restart']), False)
    else:
        source['content_count'] = len(contents)

    return source


def content_wrapper(apps_meta, status_types, hostname, track, isupdate=False):
    """Wrapper for content

    Content is packaged for Logging and distribution
    """
    return content_convert(content_process(apps_meta, status_types, hostname, track, isupdate))


def content_convert(source_wrapper):
    """Convert content from AppetiteApp to dict

    Converting the class to dict is needed for json logging and distribution
    """
    new_source_wrapper = source_wrapper.copy()

    new_source_wrapper['content'] = [content.to_dict for content in source_wrapper['content']]

    return new_source_wrapper


def render_template(content, template_values):
    """Render a jinja2 templated string against values"""
    return Template(content).render(template_values)


def get_template_vars(content):
    """Get all templated keys from jinja2 templated string"""
    env = Environment(autoescape=True)
    parsed_content = env.parse(content)
    return meta.find_undeclared_variables(parsed_content)


def merge_templates(templating_values):
    """Merge templates into a single object"""
    if isinstance(templating_values, list):
        tvalues = {}
        for dictionary in templating_values:
            tvalues.update(dictionary)
        return tvalues
    return templating_values


def template_directory(app_path, templating_values):
    """Template files

    Walks through all the files a directory and templates any jinja2 values
    found.
    """

    if not check_path(app_path):
        logger.errorout("Can not copy location that does not exist",
                        path=app_path)

    tvalues = merge_templates(templating_values)

    for path, _dir, files in os.walk(app_path):
        # sort files so logs read better and easier to get status
        files.sort()
        j2_env = Environment(autoescape=True, loader=FileSystemLoader(path))
        for filename in files:
            # Should not template version file since it may have
            # regex commands that can break templating.
            if filename.startswith(consts.VERSIONS_FILENAME):
                continue

            file_path = os.path.join(path, filename)
            try:
                file_content = j2_env.get_template(filename).render(tvalues)

                with open(file_path, 'w') as f:
                    f.write(file_content)
            except Exception as e:
                logger.errorout('Error templating file', file=file_path, error=e.message)


def move_regexed_files(regex_lines, src_path, dest_path): # pylint: disable=too-many-locals
    """Move files based on a regex filter

    Some application require precise files to be moved, overwritten and/or
    ignored.
    """
    path_errors = []
    files_included = []

    src_path_len = len(src_path) + 1

    for l in regex_lines:
        filter_split = os.path.split(l)
        src = os.path.join(src_path, filter_split[0])
        dest = os.path.join(dest_path, filter_split[0])

        if not os.path.exists(src):
            path_errors.append(l)
            continue

        filter_files = len(filter_split[1]) > 0

        if filter_files:
            # Moves files individually
            create_path(dest, True)
            files_list = [os.path.join(filter_split[0], f)for f in os.listdir(src)
                          if re.search(filter_split[1], f)]

            for f in files_list:
                src_file = os.path.join(src_path, f)
                dest_file = os.path.join(dest_path, f)
                shutil.move(src_file, dest_file)
        else:
            # Moves whole directory
            files_list = [os.path.join(root[src_path_len:], f)
                          for root, _dirs, files in os.walk(src)
                          for f in files]
            # Since folder is moved, should be one directory back in the dest
            dest_folder = REMOVE_LAST_FOLDER.sub('', dest)
            create_path(dest_folder, True)
            shutil.move(src, dest_folder)

        files_included += files_list

    return {'errors_found': len(path_errors) > 0, 'path_errors': path_errors,
            'files_moved': files_included}


class RunSingleInstance(object):
    """Class to lock script instance so other instances can not run"""
    def __init__(self, lockfile=LOCK_PATH):
        """Init RunSingleInstance
        """
        self.__filelock = None
        self.__is_running = False
        self.__checked = False

        self.set_lockfile(lockfile)

    def __enter__(self):
        """Enter RunSingleInstance class
        :return: self
        """
        self.__checked = True

        try:
            self.__filelock = open(self.__lockfile, 'w+')
            # None blocking lock
            fcntl.lockf(self.__filelock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            if self.__filelock is not None:
                self.__is_running = True
        return self

    def __exit__(self, type, value, tb): # pylint: disable=redefined-builtin
        """Exit RunSingleInstance class
        :return: None
        """
        try:
            if not self.__is_running:
                fcntl.lockf(self.__filelock, fcntl.LOCK_UN)
                self.__filelock.close()
                os.unlink(self.__lockfile)
        except Exception as err:
            logger.error("Error unlocking single instance file", error=err.message)

    def lock(self):
        """Run function to lock file
        :return: self
        """
        return self.__enter__()

    def unlock(self):
        """Unlock and delete file
        :return: None
        """
        self.__exit__(None, None, None)

    def set_lockfile(self, lockfile):
        """set lock file
        :return: None
        """
        if not self.__checked:
            self.__lockfile = lockfile

    @property
    def is_running(self):
        """Returns if the app is already running
        :return: true | false
        """
        return self.__is_running

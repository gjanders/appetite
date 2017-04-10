#!/usr/bin/env
# pylint: disable=invalid-name,no-self-use,missing-returns-doc,missing-type-doc
"""Appetite test

Unit test to externally test the internal functionality and logic of appetite.
This does not test ssh or repo calls.
"""

import os
import subprocess # nosec
import unittest
import shutil
import shlex
import json

REPO_BASE_FOLDER = "repo"

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
SCRIPT_PATH = TEST_PATH.replace('/tests', '/src')

LOG_DIR = os.path.join(TEST_PATH, '.test_log')
TMP_DIR = os.path.join(TEST_PATH, REPO_BASE_FOLDER, 'tmp')
META_DIR = os.path.join(TEST_PATH, REPO_BASE_FOLDER, 'meta')
LOG_FILE = os.path.join(LOG_DIR, 'appetite_repo.log')


def get_python_path():
    """Finds python path, useful when using IDEs testing different versions of python
    :return: None
    """
    split_lib = os.__file__.split("/lib/")
    if len(split_lib) < 2:
        # Use default
        return ""
    return "%s/bin/" % split_lib[0]


PYTHON_BIN_LOCATION = get_python_path()

# Test hostnames that match deploymentmethods and commands
TEST_HOST_LIST = [
    "splunk-lm001-0c",
    "splunk-cm001-0c",
    "splunk-ds001-0c",
    "splunk-idx001-0c",
    "splunk-idx002-0c",
    "splunk-idx003-0c",
    "splunk-idx001-1c",
    "splunk-idx002-1c",
    "splunk-idx003-1c",
    "splunk-sha001-0c",
    "splunk-shm001-0c",
    "splunk-dcm001-0c",
    "splunk-scm001-0c",
    "splunk-scm002-0c",
    "splunk-scm003-0c"
]

HOST_CLASSES = "lm cm ds idx dcm shm sha scm scs"


def set_command_cmd(ext_args=""):
    # Create the base command to run test against

    if 'config-file' not in ext_args:
        ext_args += "--config-file ../configs/demo_splunk/repo_test.conf "

    return shlex.split("%s"
                       "python appetite.py "
                       "--logging-path %s "
                       "--hosts %s %s" %
                       (PYTHON_BIN_LOCATION,
                        LOG_DIR,
                        " ".join(TEST_HOST_LIST),
                        ext_args))


COMMON_CMD = set_command_cmd()


def cmd_appetite(manifest, extra_params, num_threads=1, delete_logs=False):
    """Run appetite with defined params
    :param manifest: manifest to reference
    :param extra_params: extra params if needed
    :param num_threads: Number of threads to use
    :param delete_logs: Delete logs before running
    :return: output from appetite call
    """
    if delete_logs:
        delete_log_dir()
    create_log()

    cmd = list(COMMON_CMD) + shlex.split("--num-conns %s --apps-manifest %s %s" % (
        num_threads, manifest, extra_params))

    return subprocess.check_call(cmd, cwd=SCRIPT_PATH, shell=False) # nosec


def create_log():
    """Crete log path and starting file"""

    if not os.path.isfile(LOG_FILE):
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        with open(LOG_FILE, 'a') as touch:
            touch.write("")


def delete_log_dir():
    """Delete current test logs"""

    delete_path(LOG_DIR)


def clean_tmp_folders():
    """Delete tmp directories"""

    delete_log_dir()
    delete_path(TMP_DIR)
    delete_path(META_DIR)


def delete_path(path):
    """Delete current path"""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
    except Exception as e:
        raise Exception("Problem deleting folder; path: %s error: %s" % (LOG_DIR, e.message))


def get_entry(*args):
    """Find strings with in logs"""

    results = find_entry(LOG_FILE, *args)

    if not results:
        return

    try:
        # Log files produced are in json format
        return json.loads(results)
    except Exception as e:
        print "line: %s" % str(results)
        print e.message
        raise


def find_entry(filepath, *args):
    """Find strings in files"""

    with open(filepath, 'r+') as f:
        for line in f:
            if next((False for str_input in args if str_input not in line), True):
                return line
    return


class Test01BasicAppetiteRun(unittest.TestCase):
    """Basic appetite tests
    """
    def tearDown(self):
        clean_tmp_folders()

    def test_00_test_full_run(self):
        """Run a full install with clean systems

        If a system is new then firstrun has to be enabled and if needed templating
        """

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 1, True)

    def test_01_test_full_run_threaded(self):
        """Run a full install with threading

        Using a thread pool to run app installs
        """
        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

    def test_02_test_no_change_found(self):
        """Run the same manifest therefore no changes are found"""

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

        # Run second time
        cmd_appetite("manifest_00_fullinstall.csv",
                     "", 10, True)

        appetite_stats = get_entry("Appetite complete")

        self.assertFalse(appetite_stats['log']['changes'])

    def test_03_dups_check(self):
        """Check for dups"""

        # Look for dups
        cmd_appetite("manifest_01_dups.csv",
                     " --firstrun --templating", 10)

        # Should find 2 occurances of shm
        shm = get_entry("Dup app found", "splunk-shm")['log']
        self.assertEquals(shm['app_info']['app'], "App01")
        self.assertEquals(shm['occurences'], 2)

        # Should find 3 occurances of sha
        sha = get_entry("Dup app found", "splunk-sha")['log']
        self.assertEquals(sha['app_info']['app'], "App01")
        self.assertEquals(sha['occurences'], 3)

    def test_04_look_for_deleted_app(self):
        """Test deletion of apps"""

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

        # Delete App 4
        cmd_appetite("manifest_02_delete_apps.csv",
                     "", 10, True)

        delete_stat = get_entry('"msg": "delete"')['log']

        self.assertIn("/opt/splunk/etc/slave-apps/App04", delete_stat['cmd'])

    def test_05_changes(self):
        """Look for app changes"""

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

        # Change App 8
        cmd_appetite("manifest_03_change_app.csv",
                     "", 10, True)

        changes_found = get_entry('"msg": "Changes found"', "splunk-sha", '"app": "App08"')['log']

        self.assertTrue(changes_found)

    def test_06_check_templating(self):
        """Checks for templating"""

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

        app_location = os.path.join(TEST_PATH, "repo/tmp/hosts/splunk-cm001-0c/etc/apps/App02/App02.txt")

        # Check if value was filtered using the test/filters/example.py and comes from a config yml file
        self.assertIsNotNone(find_entry(app_location, 'text_has_been_filtered'))

        # Check if value comes from a config file (json on the command line)
        self.assertIsNotNone(find_entry(app_location, 'searchforthis'))

    def test_07_global_override(self):
        """Checks global override"""

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

        removed_file = "FileThatWillGloballyKillEverything.txt"
        global_msg = "Globally these files should not exist in the App"
        log_msg = '"%s/%s"], "hostname": "%s", "msg": "%s'

        file_location = os.path.join(TEST_PATH, "repo/tmp/hosts/splunk-cm001-0c/etc/apps/App02/local/",
                                     removed_file)

        self.assertFalse(os.path.isfile(file_location))
        self.assertIsNotNone(get_entry(log_msg % ('local', removed_file, 'splunk-cm001-0c', global_msg)))

        file_location = os.path.join(TEST_PATH, "repo/tmp/hosts/splunk-ds001-0c/etc/apps/App01/default/",
                                     removed_file)

        self.assertFalse(os.path.isfile(file_location))
        self.assertIsNotNone(get_entry(log_msg % ('default', removed_file, 'splunk-ds001-0c', global_msg)))

    def test_08_install_splunk(self):
        """Checks install splunk"""

        cmd_appetite("manifest_00_fullinstall.csv",
                     " --firstrun --templating", 10)

        splunk_install_file = "splunk_installed.txt"
        untemplated_value = "{{ nothing_happened_here }}"

        file_location = os.path.join(TEST_PATH, "repo/tmp/hosts/splunk-cm001-0c/",
                                     splunk_install_file)

        self.assertTrue(os.path.isfile(file_location))
        self.assertIsNotNone(find_entry(file_location, untemplated_value))

if __name__ == '__main__':
    unittest.main()

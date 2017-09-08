#!/usr/bin/python
"""Const values"""

CONFIG_PATH_NAME = 'configs'
VERSIONS_FILENAME = 'app_version'
VERSIONS_FILENAME_EXT = ".json"
APPS_METADATE_FILENAME = 'meta_'
TMP_IGNORE_DIR = 'ignore_tmp'

APP_MANIFEST_HEADERS = ['commitid', 'application', 'whitelist', 'blacklist', 'method']

LOGPATH = '/var/appetite'
META_DIR = 'appetite'

DEPLOYMENT_METHODS_FILENAME = "deploymentmethods.conf"

# Default version given to applications with no version
# This is supplemented with the commit id before storing to file
DEFAULT_VERSION = "1.0"

# Status Change values
META_APP_CHANGED = 'changed'
META_APP_DELETED = 'deleted'
META_APP_ADDED = 'added'
META_APP_UNCHANGED = 'unchanged'

# Lists to check app statuses
META_CURRENT = [META_APP_CHANGED, META_APP_ADDED, META_APP_UNCHANGED]
META_UPDATED = [META_APP_CHANGED, META_APP_ADDED, META_APP_DELETED]
META_CHANGED = [META_APP_CHANGED, META_APP_ADDED]

# Extensions to use with templating
JSON_EXTS = ['json']
YMAL_EXTS = ['ymal', 'yml']
TEMPLATING_EXTS = JSON_EXTS + YMAL_EXTS

HOST_LOGS_FOLDER_NAME = "logs"

# Name formatting for host names
NAME_FORMATTING = [
    {
        'name': "appclass",
        'format_type': "str"
    },
    {
        'name': "site",
        'format_type': "str"
    },
    {
        'name': "num",
        'format_type': "num"
    },
]

NAME_FORMATTING_SPLIT_TOKEN = 11110000100001111

DM_COMMANDS_SEQUENCE = ['run_first_script', 'commands', 'run_last_script']

DEFAULT_THREAD_POOL_SIZE = 10
DEFAULT_LOG_RETENTION = 30  # days
REMOTE_CMD_RUN_SLEEP_TIMER = 30  # seconds
REMOTE_AUTH_RUN_SLEEP_TIMER = 5  # seconds

# Pulling commit logs have standard names, this helps format the correctly
RENAME_COMMIT_LOG_KEYS = {
    'commit_id': "app_commit_id",
    'abbrv_commit_id': "app_abbrev_commit_id"
}

# Default (needed) columns in the manifest
DEFAULT_COLUMN_HEADER = [
    'commitid',
    'application',
    'deploymentmethod',
    'whitelist',
    'blacklist'
]

# Location within an application to look for version number
LOCATION_DEFAULT = 'default/app.conf'
LOCATION_LOCAL = 'local/app.conf'

# Var used to set up version stanza im a file
LAUNCHER_STANZA = 'launcher'
VERSION_KEY = 'version'

#!/usr/bin/python
#pylint: disable=too-complex,relative-import,no-member,too-many-nested-blocks,too-many-branches
"""AppVersioning
Module for app tracking using both app versioning and appetite versioning.

Many applications have their own application version.  This is module modifies
the application version with the commit id of the application pull.  This helps
verify that applications actually got to their source.
"""

import re
import os

import consts
import helpers


def is_stanza(line):
    """Searches string to see if it is a stanza"""
    return re.search(r"^\[.*\] *", line)


def has_version_key(line):
    """Checks to see if line has version key"""
    keyvalue = line.split('=')
    if len(keyvalue) == 2:
        # Looks for version key in file, will return the first found
        if keyvalue[0].strip().lower() == consts.VERSION_KEY:
            return True
    return False


def create_version(version, commit_id):
    """Create a version based on the version provided and the commit id"""
    return "%s_%s" % (version, commit_id)


def get_version(line, commit_id):
    """Get Version based on either default or """
    if not commit_id:
        return consts.DEFAULT_VERSION

    keyvalue = line.split('=')
    if len(keyvalue) == 2:
        # Looks for version key in file, will return the first found
        if keyvalue[0].strip().lower() == consts.VERSION_KEY:
            return create_version(keyvalue[1].strip(), commit_id)
    return create_version(consts.DEFAULT_VERSION, commit_id)


def create_version_line(new_version):
    """Create a version line to be used in configuration file"""
    return str("%s = %s\n" % (consts.VERSION_KEY, new_version))


def add_version_to_content(file_content, commit_id, version=None, remove_version=False):
    """Add version to provided configuration

    Function will search for and replace version, if version is not found it
    will add the version to the config
    """
    updated_content = []
    current_version = None
    launcher_found = False
    app_version = None
    default_version = version if version else get_version("", commit_id)

    while len(file_content) > 0:
        line = file_content.pop(0)

        # Looks for launcher stanza to add version information
        if is_stanza(line):
            launcher_found = consts.LAUNCHER_STANZA in line

            if launcher_found:
                # Look ahead for version
                for stanza_line in file_content:
                    # break if next stanza is found
                    if is_stanza(stanza_line):
                        break

                    # Look for version key and get value with commit id
                    if has_version_key(stanza_line):
                        app_version = get_version(stanza_line, commit_id)
                        break

            # Do not need stanza after this, add and skip
            if len(file_content) > 0:
                updated_content.append(line)
                line = file_content.pop(0)

        if launcher_found:
            if not remove_version:
                if not current_version:
                    # From look ahead, replace version value since it exists
                    if app_version:
                        if has_version_key(line):
                            current_version = version if version else app_version
                            updated_content.append(create_version_line(current_version))
                    else:
                        # Since version does not exist in stanza, add version
                        current_version = default_version
                        updated_content.append(create_version_line(current_version))

            # Version updates should already be done or skipped,
            # ignoring version from content
            if has_version_key(line):
                continue

        updated_content.append(line)

    if not current_version and not remove_version:
        # Launcher stanza is not found, appends to end of file
        include_nl = '\n' if len(updated_content) > 0 else ''
        current_version = default_version

        # Create basic stanza with version number
        app_config = "\r\n[%s]\r\n%s = %s" % (consts.LAUNCHER_STANZA,
                                              consts.VERSION_KEY,
                                              current_version)

        # need to add newline after since writeline does not include them
        updated_content += ['%s\n' % config_line for config_line in
                            (str(include_nl + app_config)).
                            splitlines()]

    file_content += updated_content

    return current_version


def create_app_version(app_path, commit_id):
    """Looks in application path and finds version file to update.

    Looks for valid application version and updates with commit id.
    """
    # Get the paths for the apps.conf in both locations
    default_app_path = os.path.join(app_path, consts.LOCATION_DEFAULT)
    default_local_path = os.path.join(app_path, consts.LOCATION_LOCAL)

    # Tries to get the content from both confs
    default_content = helpers.get_contents(default_app_path)
    local_content = helpers.get_contents(default_local_path)

    # update default apps.conf with new version number
    default_content = default_content if default_content else []
    add_version_to_content(default_content, commit_id)
    helpers.write_contents(default_app_path, default_content)

    # If local found, remove versions
    if local_content:
        add_version_to_content(local_content, commit_id, None, True)
        helpers.write_contents(default_local_path, local_content)

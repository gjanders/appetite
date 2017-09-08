# Configurations and templating

## Parameters
    -h, --help
<a name="param_help"></a>Show this help message and exit

    --config-file cf
<a name="param_config_file"></a>Config file used to in place of params.

    --commands-conf'
<a name="param_commands_conf"></a>Location of the command.conf file.
If this is not set the the location is the same folder as the [--config-files](#param_config_file) and a file with the name '_commands.conf_'.

    --hosts [c [c ...]]
<a name="param_hosts"></a>List of host that appetite will filter against.
Each host value is used to define [hostname](#hgv_hostname) and [ssh_hostname](#hgv_ssh_hostname).  For environments without name resolution an ip can be used to qualify the host.
For example 'splunk-cm001-0d' or 'splunk-cm001-0d:192.168.30.31'.

    --host-classes [hc [hc ...]]
<a name="param_host_classes"></a>Host classes are used to check host lists to makes sure appetite is only applied to the specified classes.  Classes are defined in the host name ( [--name-formatting](#param_name_formatting) ).  This provides a secondary layer of filtering allowing for full host lists to be entered though the command line.

    --boot-order [boot [boot ...]]
<a name="param_boot_order"></a>Uses classes to define the order in which systems are updated and booted.  If any classes are not defined, they will be updated and booted last.

    --tmp-folder dir
<a name="param_tmp_folder"></a>Folder where host apps and tars are created.

    --scratch-dir dir
<a name="param_scratch_dir"></a>Directory where Appetite runs will store files.

    --apps-folder f
<a name="param_apps_folder"></a>Location of apps for deployment relative to repo location.

    --apps-manifest m
<a name="param_apps_manifest"></a>Location/filename of manifest located in the config folder in the repo.

    --repo-url repourl
<a name="param_repo_url"></a>Repo url location.

    --repo-branch repobranch
<a name="param_repo_branch"></a>Repo branch.

    --ref-name p
<a name="param_ref_name"></a>Location where the pulled repo and [--tmp-folder](#param_tmp_folder) is created.
This is created in the [--scratch-dir](#param_scratch_dir) directory.
This is used to tag apps.
Defining a new ref-name will create a copy of the repo that appetite will check against.

    --template-files [f [f ...]]
<a name="param_template_files"></a>Templating key value files(*.json and/or *.ymal)
This can be used to template values in files.

    --template-json v
<a name="param_template_json"></a>Templated values entered via json object through command line.  This will be combined with templated files loaded in.

    --template-filtering
<a name="param_template_filtering"></a>Filter/Modifies templated values using an external function.
  Appetite loads in the function at runtime and can be in any location the script has access to.

Unit testing testing uses [example.py](.//script/test/filters/example.py) for reference.
Using example.py the format of the param would be:

`test/filters/example.py:FilterFunctions.test_filtering`

    --name-formatting pre{{appclass}}{{'%03d'%num}}{{site}}post
<a name="param_name_formatting"></a>Jinja2 name formatting of host names.
This is used to determine class, pre and post fix.

    --app-folder folder
<a name="param_app_folder"></a>This is the root location from where all apps can be installed from.

    --app-binary binary
<a name="param_apps_binary"></a>Based on the [--app-folder](#param_app_folder) on remote host, the relative location of service.  This is used for outside calls needed with the service.

    --logging-path p
<a name="param_logging_path"></a>Location where logs are generated and rotated.

    -l u, --ssh-user u
<a name="param_ssh_user"></a>The default ssh user to log into the instances.

    -i f, --ssh-keyfile f
<a name="param_ssh_keyfile"></a>The ssh keyfile used to log into the service instances.

    -p p --ssh-port p
<a name="param_ssh_port"></a>The ssh port (default 22).

    --num-conns t
<a name="param_num_conns"></a>Number of concurrent threads that deal with updating hosts.
This is dependent on [--boot-order](#param_boot_order) which can limit the number of concurrent hosts i.e., if there's one host that has a defined class, only one host will update.

    --new-host-brakes
<a name="new_host_brakes"></a>If a new host if found, override [--num-conns](#param_num_conns) count to 1.

    -d, --debug
<a name="param_debug"></a>Turns on debugging output.

    --disable-logging
<a name="param_disable_logging"></a>Turn off message logging.  Good for debugging.

    -s, --silent
<a name="param_silent"></a>Turn off stdout on screen.  Good for background processing.

    --templating
<a name="param_templating"></a>Turns on templating where variables in application can be replaced with templated values.
This is explained later in this document.

    --firstrun
<a name="param_firstrun"></a>If applications on a server need to be bootstrapped, this will trigger the logic to correctly distribute apps.

This will only run if there is no manifest file located on the instance.

On firstrun instances, the whole app is copied including any files/folders excluded in the [install\_inclusion\_file](.//deploymenthods.md#install_inclusion_file).

For example, a Splunk Indexer needs to be connected to the Cluster Master before the Cluster Master can push configurations to it. This option will allow the initial application configuration to be placed onto the Indexer in the slave-apps directory to allow it to connect to the Cluster Master, and then the subsequent runs that application will not be written by Appetite.

    --skip-repo-trigger
<a name="param_skip_repo_trigger"></a>Skips the manifest trigger and will always check the manifest against the host.  This good for testing unit testing and CI.

    --build-test-apps
<a name="param_build_test_apps"></a>Creates test apps based on manifest.  Used for testing.

    --dry-run
<a name="param_dry_run"></a>Turns off all git and ssh commands.
Used for testing Appetite logic and seeing what the payload will be.

    --no-strict-commitids
<a name="param_no_strict_commitids"></a>No commit id version lock for apps. Will use the latest app when deploying.

    --install-ignore
<a name="param_install_ignore"></a>Global install ignore check and remove files/folders in every app.

    --site-override
<a name="param_site_override"></a>By default all updates will be done a single site at a time in [--boot-order](#param_boot_order).  This will override that setting and Update all host within a [--boot-order](#param_boot_order).

    --deployment-methods-file
<a name="deployment_methods_file"></a>The deployment methods file appetite will look for.  
default: `deploymentmethods.conf`

## Templating

[Jinja2](http://jinja.pocoo.org/) templating is used to add variables to app configuration files and command lines.
Templating is based on key/value pairs that can come from the following sources:

* Key/value JSON object passed in via cli parameters ( [--template-json](#param_template_json) ).
* JSON and/or [YAML](http://www.yaml.org/start.html) files referenced via cli parameters ( [--template-files](#param_template_files) ).
* [Host generated variables](#templating_host_generated).
* [App generated variables](#templating_app_generated).

The sources are combined into a single key/value dictionary that the Jinja2 templating can use.

Possible use from example [Example YAML](.//configs/demo_splunk/sample_config.yml)

        user: "{{ user }}"
        pass: "{{ password }}"


### <a name="templating_host_generated"></a>Host generated variables.

These key/values are generated within Appetite (AppetiteHost class).
These can be referenced by app files and [commands.conf](.//configs/demo_splunk/commands.conf).

The following variables are available:

* hostname - Name of host. This is generated from the [--hosts](#param_hosts)<a name="hgv_hostname"></a>.
* app_class - Class of host.  This is extracted from the hostname and is reference from [--host-classes](#param_host_classes) parameter.
* site - Site extracted from hostname.  This is used to group runs per [--boot-order](#param_boot_order).
* host_index - Host number pulled form the hostname.
* ssh_hostname - Either the hostname or the ip.  Determined from the entered [--hosts](#param_hosts) data. <a name="hgv_ssh_hostname"></a>
* restart - Host will be restarted.  Generated from manifest.
* updates - If hosts have been updated (bool). Generated from manifest change logic.
* host_groups - Hostnames split into groups.
     * app_class[ 'user defined host class' ] - A list of hosts based on a host class.
     * all - A list of all hosts.
     * ref[ 'hostname' ] - Gives the SSH Connection hostname/IP for a given hostname.
     * limited_hosts - List of host based on `limit_to_hosts` and `exclude_hosts` in commands.conf.


Example:
The first 'd' is replaced with an 's' in the host name.

        https://{{ hostname | replace("d", "s", 1) }}


### <a name="templating_app_generated"></a>App generated variables.

These key/values are generated within Appetite (AppetiteApp class).
This can only be referenced by app files.

The following variables are available:

* app - Manifest app name.
* app_clean - Cleaned app name.
* source_hostname - hostname where app is installed.
* method_info - Info from deploymentmethods.conf about where and how the app is deployed.
    * name - name of deployment method.
    * commands - list of cmd commands to run with app update/install.
    * path - path where app is installed.
    * update_method - 'copy' | 'copy_in_place'.
    * delete_first - Delete application before installing (False).
    * restart - Restart process after install (False).
    * is_firstrun - Is the app being installed on a blank system.
    * skip_templating - Provide override against [--templating](#param_templating).
    * scripts - list of commands to run before and/or after **commands**.

Example:
List is app name.

        App Name: {{ app }}


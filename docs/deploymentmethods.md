# Deployment Methods

This is how the application gets installed.  This is referenced in the manifest and obfuscates the install process from the writers of the manifest.  This document is heavy with splunk examples but can be applied to other applications/services.

## Settings
### GLOBAL

Use the _[default]_ stanza to define any global settings.
* Global settings can only be applied globally.
* If a global attribute is defined at in a specific stanza, it will be ignored

* **app_name_filter** = <regex\>
    * Regex that filters the name of the deployed application.
    * Anything matched by the regex will be removed from the application name.
    * Useful to have different versions of the same application in the same repository.
    * Example 1: app_name_filter = [\[].*

            App Name in Repository |      App Name Deployed to Host

            Splunk_TA_nix          |      Splunk_TA_nix
            Splunk_TA_nix[idx]     |      Splunk_TA_nix

    * Example 2: app_name_filter = [\(].*[\)]

            App Name in Repository |      App Name Deployed to Host

            Splunk_TA_nix          |      Splunk_TA_nix
            Splunk(DEV)_TA_nix     |      Splunk_TA_nix
            Splunk_TA_nix_DEV      |      Splunk_TA_nix_DEV

    * Use only allowed special characters for files/folders.
    * Default is [\[].*
<a name="install_inclusion_file"></a>
* **install_inclusion_file** = <file name\>
    * File which lists files/directories to be included in the deployed application.
    * File needs to be created in the root of the application.
        * $SPLUNK_HOME/etc/apps/<app_name>/<install_inclusion_file>
    * Regex used only for matching file name. Folder/Subfolders are literal match (not regex).
    * Do not include a header in the file, just a list separated by new lines.
    * Only applies to files specified in the "install_ignore" setting in the Deployment Stanzas
    * Example: install_inclusion_file = "app_inclusion.txt"

            lookups/                    |   Includes all files and folders recursively in lookups/
            lookups/test.csv            |   Includes only test.csv in the lookups directory
            lookups/col(o|ou)r\.csv     |   Includes color.csv OR colour.csv in the lookups directory
            local/.*                    |   Includes all the files in the local folder
            local/data/                 |   Includes all files and folders recursively under local/data/

    * Default is empty

### DEPLOYMENT METHODS
These options may be set under an **[<deployment_method>]** entry.

The following settings only are applied to **<deployment_method\>** stanzas.

**[<deployment_method>]**

This stanza enables properties for the given <deployment_method>.
* A deploymentmethods.conf file can contain multiple stanzas for any number of different methods.
* Follow this stanza name with any number of the following attribute/value pairs, as appropriate for what you want to do.

**path** = <path on destination server\>

A path relative to $SPLUNK_HOME on the Splunk server where the application will be deployed.
* Default is empty
* Examples:

        etc/apps/
        etc/shcluster/apps/
        etc/master-apps/
        etc/slave-apps/
        etc/deployment-apps/

**delete_first** = true|false

* Removes the application folder first before installing the application.
* Insures a clean installation of an application.
* Useful for methods being deployed to cluster masters or deployers.
* Defaults to false.

**install_ignore** = <directory|file list>
* List of directories or file names to ignore when deploying an application.
* Appetite will package the application as if these directories or files never existed.
* IMPORTANT: It is wise to include the lookups directory so as to not overwrite lookups changed locally on the server!
* Separate each entry by a semi-colon (;).
* Useful for deploying applications to a standalone search head to prevent local files from being overwritten.
* Example:

            * lookups/;metadata/local.meta;local/
            Excludes all files/folders in the lookups directory.
            Excludes local.meta file in the metada directory.
            Excludes all files/folders in the local directory.

* Example Entries in List:

            lookups/                    |   Includes all files and folders recursively in lookups/
            lookups/test.csv            |   Includes only test.csv in the lookups directory
            lookups/col(o|ou)r\.csv     |   Includes color.csv OR colour.csv in the lookups directory
            local/.*                    |   Includes all the files in the local folder
            local/data/                 |   Includes all files and folders recursively under local/data/

Default is empty.

**update_method** = copy|copy_in_place
* Determines how an application is installed.
     * copy - copies the entire application directory into the path.
        If path is "etc/apps/", it will copy the whole directory (Splunk_TA_nix) into the path.
     * copy_in_place - copies the individual files into the path, not the whole directory.
        If path is "etc/licenses/enterprise/", it will copy the files with an app containing licenses into the path, not the directory itself.
* Default is empty.

**restart** = true|false
* If true, restarts service on the client when a member app or a directly configured app is updated.  This is defined in the [commands.conf](../configs/demo_splunk/commands.conf).
* Defaults to false.

**skip_templating** = true|false
* If templating is turned on.  This can override and turn templating off for the deployment methods.
* Useful for apps installed that are large and have a lot of binaries.
* Defaults to false.

**command1** = <command\>
* Commands are dictated in the [commands.conf](../configs/demo_splunk/commands.conf) on the Appetite server.
* Unlimited commands can be listed in order to be run.
     * command1 = <command\>
     * command2 = <command\>
     * command'n' = <command\>
* Example Commands by Splunk Server:
     * Cluster Master       |   cluster
     * Deployment Server    |   reload_ds
     * Deployer             |   shcluster
* Default is empty.

**script1** = <command\>
* Commands are dictated in the [commands.conf](../configs/demo_splunk/commands.conf) on the Appetite server.
* scripts can be listed before and after 'command' calls.  Limited to just running commands.
     * script1 = <command\>
     * script2 = <command\>
     * command'n' = <command\>
     * script3 = <command\>
* Example Commands by Splunk Server:
     * Maintenance mode enabled |   maintenance_mode_enabled
     * Maintenance mode disable |   maintenance_mode_disable
     * Stop Splunk Service      |   stop_splunk
     * Start Splunk Service     |   start_splunk
* Default is empty.

###STARTUP BOOTSTRAP METHODS
These options may be set under an **[StartupBootstrap_<name\>]** entry.

The following settings only are applied to **[StartupBootstrap_<name\>]** stanzas.

Startup Bootstrap classes are a specific type of deployment method used during first run.

This allows an application deployed to one type of server class and method to be changed to another type of server class and method.

This feature allows applications to be deployed a certain way without duplicating manifests.

Deployment method commands specified in the <deployment_method> stanzas are not used.

**[StartupBootstrap_<name\>]**
* This stanza enables properties for a given StartupBootstrap_<name>.
* A deploymentmethods.conf file can contain multiple stanzas for any number of
  Bootstrap different methods.
* Follow this stanza name with any number of the following attribute/value
  pairs, as appropriate for what you want to do.

**app_class** = <server_class\>
* Class of the server you wish to change for first run.
* Default is empty.

**update_method** = <deployment_method\>
* Deployment method you wish to change for first run.
* Default is empty.

**ref_class** = <server_class\>
* New class of the server you wish to change to for first run.
* Default is empty.

**ref_method** = <deployment_method\>
* New deployment method you wish to change to for first run.
* Default is empty.

EXAMPLES AND EXPLANATIONS
* Example1
* On first run, any application deployed with the "ClusterMaster" method to the "cm" class of servers will now be
* deployed to the "idx" class of servers using the "ClusterMaster_FirstRun" method.

        [StartupBootstrap_idx]
        app_class: cm
        update_method: ClusterMaster
        ref_class: idx
        ref_method: ClusterMaster_FirstRun

* Example2
* On first run, any application deployed with the "Deployer" method to the "dep_shcluster" class of servers will
* now be deployed to the "shcluster" class of servers using the "StandAlone_FirstRun" method.

        [StartupBootstrap_shcluster]
        app_class: dep_shcluster
        update_method: Deployer
        ref_class: shcluster
        ref_method: StandAlone_FirstRun

**Explanation**

Referencing Example2, the first time Splunk is setup, it is impossible to send applications to the deployer to be applied to the cluster since these server classes are not yet configured.  Instead of creating a whole new manifest file for a one time deployment, startup stanzas were created which override the normal deployment stanza for the first run only.  Applications that were destined for the Search Head Cluster via the deployer will be deployed to the cluster manually on the first run, and on subsequent runs, will utilize the Deployer method for future deployments.

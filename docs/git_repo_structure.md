#Git Repo

Appetite utilizes Git as its version control system.  Appetite does not care which flavor of the Git server you use (i.e. Github, Gerrit, Stash, GitLab...). The GIT Repository stores the applications and the configurations of how those applications will be deployed / installed. Multiple repos can be configured.

## Structure
Appetite requires at least 2 directories in the repo: apps and configs.

## Apps
The apps directory can be called anything (defined by the [--apps-folder](../README.md#param_apps_folder) in Appetite). It is where Splunk applications will be stored.
You can have multiple apps directories.  For example, one could be called apps, and the other called base_apps.  This could be useful if you wanted to separate applications downloaded with ones developed in house.

## Configs
The configs folder contains configurations and must be called config.  It contains the [deploymentmethods.conf](../script/test/repo/appetite/config/deploymentmethods.conf) as well as the [manifest](./manifest.md) for the apps directory. Each apps directory will need to have its own corresponding manifest file.  They are differentiated by the name of the file (manifest_<app directory>.csv)

* Directory is called **apps**, the manifest file should be called **manifest_apps.csv**.
* Directory is called **baseapps**, the manifest file should be called **manifest_baseapps.csv**.

## Example
The following Splunk example contains a repo structure with 2 <app directory>: apps, base_apps

| Directory 	| Apps / Files           	| Description                                 	|
|-----------	|------------------------	|---------------------------------------------	|
| apps/     	|                        	| Apps downloaded from Splunkbase             	|
|           	| Splunk_TA_nix          	|                                             	|
|           	| Splunk_TA_nix[DEV]     	|                                             	|
|           	| Splunk_TA_windows      	|                                             	|
| base_apps/ 	|                        	| Apps created internally                     	|
|           	| Interal_auth_base      	|                                             	|
|           	| Internal_cluster_base  	|                                             	|
| configs/  	|                        	|                                             	|
|           	| deploymentmethods.conf 	|                                             	|
|           	| manifest_apps.csv      	| Manifest relating to the apps directory     	|
|           	| manifest_baseapps.csv  	| Manifest relating to the baseapps directory 	|

[For Appetite testing, only base_apps are used.](../script/test/repo/appetite/base_apps)

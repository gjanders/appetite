
#Manifest
The manifest is a csv file which determines which application goes to what server and how the application will be deployed. Empty fields must be represented with a comma.


## Sample Manifest

| CommitID 	| Environment 	| Application      	| DeploymentMethod    	| Whitelist            	    | Blacklist                  	| Comments                                                                                                          |
|-----------|---------------|-------------------|-----------------------|---------------------------|-------------------------------|-------------------------------------------------------------------------------------------------------------------|
| c241c6e  	| PRODUCTION    | STA_nix    	    | Deployer             	| splunk-dc.*p$         	|                            	| TA_nix app goes to all Search Head Cluster members via the Deployer.                                             	|
| 1b17b67  	| PRODUCTION    | TA_nix    	    | DeploymentServer    	| splunk-ds.*p$         	|                            	| TA_nix app goes to the deployment server. Gets pushed to all the UF and IUF to know how to talk to the indexers. 	|
| 7a2ecf2  	| PRODUCTION    | TA_nix    	    | Cluster_Master        | splunk-cm.*p$         	|                            	| TA_nix app goes to all Indexers via the Cluster Master.                                                           |
| c241c6e  	| PRODUCTION    | TA_nix    	    | StandAlone         	| splunk-.*p$           	| splunk-idx.*p$,splunk-sc.*p$ 	| TA_nix app goes to all Stand Alone servers. (NOT directly to Indexers or directly to Search Head Clusters)       	|
| 92dba73  	| PRODUCTION    | auth_users 	    | StandAlone          	| splunk-(cm\|lm\|ds).*p$ 	|                            	| auth_users-LM_DS_MS app goes to the License Master, Deployment Server and the Cluster Master.                     |
| 7a2ecf2  	| TESTING       | TA_nix    	    | Deployer           	| splunk-dc.*t$         	|                            	| TA_nix app goes to all Search Head Cluster members via the Deployer.                                             	|
| 1b17b67  	| TESTING       | TA_nix    	    | StandAlone        	| splunk-.*t$           	| splunk-idx.*u$,splunk-sc.*u$ 	| TA_nix app goes to all Stand Alone servers. (NOT directly to Indexers or directly to Search Head Clusters)       	|
| 7a2ecf2  	| SANDBOX      	| TA_nix    	    | Cluster_Master        | splunk-cm.*s$         	|                            	| TA_nix app goes to all Indexers via the Cluster Master.                                                           |
| 1b17b67  	| SANDBOX       | TA_nix    	    | StandAlone         	| splunk-.*s$           	| splunk-idx.*d$,splunk-sc.*d$ 	| TA_nix app goes to all Stand Alone servers. (NOT directly to Indexers or directly to Search Head Clusters)       	|


#Fields

##CommitID
**REQUIRED** - CommitID referers to the commit, otherwise a change has been made to your local repo.  This commit ID represents a snapshot of the code in the repo, which is used for versioning in Appetite.

##Environment
An arbitrary field used for differentiating applications in different environments. This is not used by Appetite.

##Application
**REQUIRED** - The name of the application directory in the repo.

##DeploymentMethod
**REQUIRED** - The name of the deployment method defined as stanzas in the deploymentmethods.conf.  This determines the specifics of how and where the application is deployed and installed.

##Whitelist
**REQUIRED** - A comma separated list of the hostname(s) where the application will be deployed. Can be explicit or a regex to represent the DNS name of the server.


| Example  | Sample Regex                 | Description                                                  |
|----------|------------------------------|--------------------------------------------------------------|
| Example1 | splunk-ds.*p$                | represents the deployment server in production only          |
| Example2 | splunk-(cm\|lm\|ds).*p$      | represents 3 different classes of servers in production      |
| Example3 | splunk-idx.*p$,splunk-sc.*d$ | represents 2 different classes of server in development only |

##Blacklist
A comma separated list of the hostname(s) where the application will NOT be deployed. Can be explicit or a regex. The blacklist is applied after the white list.
Examples same as the Whitelist.
---
layout: default
title: "Aug 27, 2020: Google Summer of Code '20 - Cloud Plugin"
parent: News
nav_order: 3
---

# Google Summer of Code '20 - Cloud Plugin

### A starter to the CueCommander cloud plugin; work done for Google Summer of Code '20

#### August 27, 2020

---

A blog post and starter material for the Cloud Plugin - work done during Google Summer of Code '20 on creating a CueCommander
plugin that can be used to manage cloud pools from OpenCue.

Author : [Shiva Kannan](https://github.com/shiva-kannan)

Please feel free to reach out at [opencue-user@lists.aswf.io](opencue-user@lists.aswf.io) if you have questions/feedback about this work.

---

## Summer of code proposal

The main proposal consisted of the plan of action for the 3 months of development, which included research about
finding a common language among cloud providers when it came to managing a pool of instances and the ability to create, delete
and resize these cloud groups through their API from the OpenCue interface.

I took Google Cloud Platform as the primary cloud provider and tried to find parallels in other providers and
started designing the main API around it. 

A [Design Document](https://docs.google.com/document/d/1cCPrZsM8fRbcluTppcuPFQ6_tfQo5rZE9W2m6Hms8pw/edit?usp=sharing)
about the initial design was then shared with the community for feedback and review which included the specs of the API
(which changed over the course of 3 months) and the API matrix which shows what the parallels in each provider are.

 
## Cloud plugin source code

The code base for this plugin is currently on the [cloud-plugin](https://github.com/AcademySoftwareFoundation/OpenCue/tree/cloud-plugin)
branch of the OpenCue repo.

## Design overview

### API design overview

Most cloud providers have the ability to manage a group of instances that can be created using a VM template/source VM and can be
managed as a single entity instead of managing separate instances.
They go by different names in different providers:
[Instance Groups (GCP)](https://cloud.google.com/compute/docs/instance-groups),
[Scale Sets (Azure)](https://azure.microsoft.com/en-us/services/virtual-machine-scale-sets),
[Auto Scaling Groups (AWS)](https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html).

The design takes into consideration how each of the cloud provider's API handle creation/scaling/deletion of these entities
and how they will be used by the plugin's single interface to manage multiple cloud provider's entities.

The design consists of two main abstract classes:

1. [CloudManager](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L73)

    CloudManager class is the interface between the API and the widget. The CloudManager is also an abstract class
    that will be implemented by each registered provider.
    This abstract class handles the following:
    
    * [connect()](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L119):
    Connection mechanism to the cloud provider through its corresponding API.
    
    * [create_managed_group()](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L100):
    Creation of a cloud pool group (CloudInstanceGroup in the API terminology).
    
    * [get_all_groups()](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L112):
    Lists all the cloud pool groups that are available in the cloud provider's project.
    
    `Google Cloud Platform` implementation of this class can be found here : [GoogleCloudManager](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/gce_api.py#L115)

2. [CloudInstanceGroup](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L18)

    The CloudInstanceGroup abstract class is the container that handles the cloud provider's managed group entity.
    This takes care of the following:
    
    * Handles setting important attributes like name, id, group's instances and the status of the cloud group.
    
    * [resize()](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L31):
    Resizing the group (scaling up/down). Currently it's left to the cloud provider to take care of which instances to
    remove during the process of scaling down.
    
    * [delete_cloud_group()](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/api.py#L58):
    Deletion of the cloud group from the cloud provider.
    
    `Google Cloud Platform` implementation of this abstract class can be found here: [GoogleCloudGroup](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/pycue/opencue/cloud/gce_api.py#L22)

### Plugin widget design

The `CloudManager` is a plugin for CueCommander. There are **three** levels to implementing this entire widget:

1. Creating the widget inside of the [plugins](https://github.com/AcademySoftwareFoundation/OpenCue/tree/526efee2fbf8c442a8e9d631e1806854463c4301/cuegui/cuegui/plugins) directory. 
The module level variables to be defined for the plugin are mentioned in the docs of the [plugin registering script](https://github.com/AcademySoftwareFoundation/OpenCue/blob/526efee2fbf8c442a8e9d631e1806854463c4301/cuegui/cuegui/Plugins.py). 
This helps registering the plugin, making it show up in the submenu and making it launch-able through the menu item.

2. Implementing `AbstractDockWidget` for the [CloudManagerDockWidget](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/cuegui/cuegui/plugins/CloudManagerPlugin.py#L31) to create a dockable widget inside of the CueCommander interface. 

3. The plugin itself then puts together two separate widgets:

    * [CloudManagerTreeWidget](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/cuegui/cuegui/CloudManagerWidget.py#L63): 
    This implements the [AbstractTreeWidget](https://github.com/AcademySoftwareFoundation/OpenCue/blob/526efee2fbf8c442a8e9d631e1806854463c4301/cuegui/cuegui/AbstractTreeWidget.py) class which provides very useful methods to handle the way data has 
    to be displayed in the widget.
    
    * [CloudGroupCreateDialog](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/cuegui/cuegui/CloudGroupDialog.py#L28):
    Which is used outside of the tree view and launched when the `Add Cloud Group` button is clicked on the plugin.
    
The interface uses the main `CloudManager` api, mentioned above, as the entry point to then get all cloud groups
associated with all the registered cloud providers.

## Cloud plugin setup

### Google compute engine setup

Listing the minimum requirements for the cloud plugin to work with GCE:

1. For your OpenCue  deployment, make sure that the GCE nodes are able to reach your Cuebot on port `8443` and for Cuebot to talk to RQD, make sure Cuebot is able to reach port `8444` on the nodes.
In my approach, I deployed Cuebot on GCE itself and the configuration was relatively simple. If you are running Cuebot locally, either configure the firewall rules in both directions or have a VPN
connection to GCP.

2. GCP project with Compute Engine API and Cloud Logging API enabled.

3. Follow [Application Default Credentials](https://cloud.google.com/sdk/gcloud/reference/auth/application-default) to setup a easy credentials access for the google APIs that the plugin uses.

4. Once you setup `Application Default Credentials`, the APIs should pick it up automatically for authentication. Please refer to [passing credentials manually](https://cloud.google.com/docs/authentication/production#auth-cloud-implicit-python)
if otherwise.

5. Modify the [cloud_plugin_resources.yaml](https://github.com/AcademySoftwareFoundation/OpenCue/blob/d4a2eca93d271dacb13ca2aaba9b531642c1dc6b/cuegui/cuegui/config/cloud_plugin_resources.yaml)
under the `cuegui/config` directory to setup your GCP project name and the zone name that the API will use to access the resources from.

6. At least one instance template setup on the cloud: I was using a RQD Blender docker image uploaded as an
[Instance Template](https://cloud.google.com/compute/docs/instance-templates) with its appropriate VM type. 
Few things to note here regarding Instance Templates:

    * The docker image I used launched RQD using the container's startup command so I didn't have to explicitly specify any startup script.
    
    * If you are using a custom setup/running GCE instances without containers, make sure the startup script for the VM launches RQD when the VM is provisioned.
    
    * The `CUEBOT_HOSTNAME` environment variable must be set for RQD to point to Cuebot. In my deployment, this env variable was set to the internal IP address of Cuebot running on GCE.

### Cloud plugin interface

The Cloud plugin should be available to launch from the menu bar by navigating:
**Views/Plugins -> CueCommander -> Cloud Plugin**

1. The cloud plugin interface consists mainly of two components:
    1. Main window which shows the list of cloud groups available with all registered providers.
    2. A cloud group addition dialog that can be used to create a cloud group from the interface itself.

### Cloud Plugin functionality

1. To start create a cloud pool group, use the `Add Cloud Group` button to launch the
dialog that will allow you to create a cloud group.

![Add Cloud Group Dialog](/assets/images/news/AddCloudGroupDialog.png)

2. If the API request is successful you should now see an entry in the Cloud Plugin's main interface.

![After cloud group addition](/assets/images/news/MainInterfacePostAddition.png)

3. The right-click content menu has two additional functionality:
    1. Resizing (scaling up/down) the number of instances in a group.
    2. Deleting the group altogether.

![Cloud Plugin Context Menu](/assets/images/news/CloudPluginContextMenu.png)

4. Once these cloud instances startup and RQD launches, you should see these nodes appear in the Monitor Hosts plugin, after which OpenCue will be able to send jobs to these hosts.

## Further work and updates

1. An Azure plugin that uses the same interface is currently a work in progress.
A draft PR for the same can be found here: [Azure Plugin PR](https://github.com/AcademySoftwareFoundation/OpenCue/pull/771).

2. [Local operation caching](https://github.com/AcademySoftwareFoundation/OpenCue/issues/773).

3. [AWS integration](https://github.com/AcademySoftwareFoundation/OpenCue/issues/774) for the cloud plugin.

4. Better integration with the MonitorHosts plugin: [Cloud group source for MonitorHosts plugin](https://github.com/AcademySoftwareFoundation/OpenCue/issues/775).

This project aimed to enhance OpenCue's cloud integration capabilities and improve scalability for cloud-based rendering workflows.
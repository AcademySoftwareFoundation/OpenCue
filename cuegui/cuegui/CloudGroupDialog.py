#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


"""
Helps create a cloud group from the cloud manager interface
"""

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Utils
import opencue.cloud.api


class CloudGroupCreateDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle("Create Cloud Group")
        self.resize(500, 200)

        layout = QtWidgets.QGridLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QtWidgets.QLabel("Service: ", self), 0, 0, 1, 2)
        self.__services_dropdown = CloudServicesCombo(selected="google", parent=self)
        layout.addWidget(self.__services_dropdown, 0, 2, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Select Template/Image: ", self), 2, 0, 1, 2)
        self.__templates_dropdown = CloudGroupTemplatesCombo(self)
        layout.addWidget(self.__templates_dropdown, 2, 2, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Group Details: ", self), 3, 0, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Name of group: ", self), 4, 0, 1, 1)
        self.__groupname_text_input = QtWidgets.QLineEdit()
        layout.addWidget(self.__groupname_text_input, 4, 2, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Number of Instances: ", self), 5, 0, 1, 1)
        self.__number_of_instances = QtWidgets.QLineEdit()
        layout.addWidget(self.__number_of_instances, 5, 2, 1, 2)

        self.__btnCreateGroup = QtWidgets.QPushButton("Create Group")
        layout.addWidget(self.__btnCreateGroup, 6, 1, 1, 2)

        self.__templates_dropdown.refresh(cloud_group=self.__services_dropdown.get_provider())
        self.__services_dropdown.currentIndexChanged.connect(self._populateTemplates)
        self.__btnCreateGroup.clicked.connect(self._createCloudGroup)

    def _populateTemplates(self):
        # TODO: When another provider is added, check this functionality
        """
        Use to query the templates associated with a particular cloud provider when the dropdown of
        cloud providers is switched
        :return:
        """
        pass

    def _createCloudGroup(self):
        group_name = self.__groupname_text_input.text()
        instances = self.__number_of_instances.text()
        template = self.__templates_dropdown.get_template_data()
        try:
            request = self.__services_dropdown.get_provider().create_managed_group(name=group_name, size=instances,
                                                                                   template=template)
            if request:
                self.close()
        except opencue.cloud.api.CloudProviderException as e:
            cuegui.Utils.showErrorMessageBox(text="{} {} request error!".format(e.provider, e.error_code),
                                             detailedText=e.message)


class CloudServicesCombo(QtWidgets.QComboBox):
    """
    A combo box for cloud services selection
    """
    def __init__(self, selected="google", parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self._cloud_providers = {}
        self.refresh()
        self.setCurrentIndex(self.findText(selected))

    def refresh(self):
        self.clear()
        cloud_providers = opencue.cloud.api.CloudManager.get_registered_providers()
        # Connect for all the registered providers
        for provider in cloud_providers:
            provider.connect(cloud_resources_config=self.get_cloud_resources_config())
        for provider in cloud_providers:
            self.addItem(provider.signature())
            self._cloud_providers[provider.signature()] = provider

    def get_provider(self):
        return self._cloud_providers[str(self.currentText())]

    def get_cloud_resources_config(self):
        cloud_config_resources_path = "{}/cloud_plugin_resources.yaml".format(cuegui.Constants.DEFAULT_INI_PATH)
        cloud_resources_config = cuegui.Utils.getResourceConfig(cloud_config_resources_path)
        return cloud_resources_config


class CloudGroupTemplatesCombo(QtWidgets.QComboBox):
    """
    Combo box for listing the available templates/images in the service provider
    """
    def __init__(self, parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self._templates = {}

    def refresh(self, cloud_group):
        """
        :param cloud_group: opencue.cloud.api.CloudInstanceGroup
        :return:
        """
        self.clear()
        templates = cloud_group.list_templates()
        for template in templates:
            self.addItem(template["name"])
            self._templates[template["name"]] = template

    def get_template(self):
        return str(self.currentText())

    def get_template_data(self):
        return self._templates[self.get_template()]

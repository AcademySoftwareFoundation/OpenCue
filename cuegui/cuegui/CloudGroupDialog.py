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

        main_layout = QtWidgets.QVBoxLayout(self)

        start_layout = QtWidgets.QGridLayout(self)
        start_layout.setSpacing(10)

        self.registered_cloud_providers = opencue.cloud.api.CloudManager.get_registered_providers()

        for provider in self.registered_cloud_providers:
            provider.connect(cloud_resources_config=self.get_cloud_resources_config())

        start_layout.addWidget(QtWidgets.QLabel("Service: ", self), 0, 0, 1, 2)
        self.__services_dropdown = CloudServicesCombo(registered_providers=self.registered_cloud_providers,
                                                      selected="google", parent=self)
        start_layout.addWidget(self.__services_dropdown, 0, 2, 1, 2)

        main_layout.addLayout(start_layout)

        horizontal_line = QHLine()
        main_layout.addWidget(horizontal_line)

        self.cloud_providers_widgets = {}

        google_templates_widget = GoogleTemplateWidget(google_manager=list(filter(lambda x: x.signature() == "google",
                                                                                  self.registered_cloud_providers)),
                                                       parent=self)
        main_layout.addWidget(google_templates_widget)
        self.cloud_providers_widgets["google"] = google_templates_widget

        azure_templates_widget = AzureTemplateWidget(azure_manager=list(filter(lambda x: x.signature() == "azure",
                                                                               self.registered_cloud_providers)),
                                                     parent=self)
        main_layout.addWidget(azure_templates_widget)
        self.cloud_providers_widgets["azure"] = azure_templates_widget

        self._populateTemplates()
        self.__services_dropdown.currentIndexChanged.connect(self._populateTemplates)

    def _populateTemplates(self):
        """
        Use to query the templates associated with a particular cloud provider when the dropdown of
        cloud providers is switched
        :return:
        """

        for widget in self.cloud_providers_widgets.values():
            widget.hide()

        current_selected_provider = self.__services_dropdown.get_provider()
        self.cloud_providers_widgets[current_selected_provider.signature()].show()

    def get_cloud_resources_config(self):
        """
        :return: YAML cloud resources config returned as a dict
        """
        cloud_config_resources_path = "{}/cloud_plugin_resources.yaml".format(cuegui.Constants.DEFAULT_INI_PATH)
        cloud_resources_config = cuegui.Utils.getResourceConfig(cloud_config_resources_path)
        return cloud_resources_config


class CloudServicesCombo(QtWidgets.QComboBox):
    """
    A combo box for cloud services selection
    """
    def __init__(self, registered_providers, selected="google", parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.registered_providers = registered_providers
        self._cloud_providers = {}
        self.refresh()
        self.setCurrentIndex(self.findText(selected))

    def refresh(self):
        self.clear()

        for provider in self.registered_providers:
            self.addItem(provider.signature())
            self._cloud_providers[provider.signature()] = provider

    def get_provider(self):
        """
        :return: Manager object of the chosen cloud provider
        """
        return self._cloud_providers[str(self.currentText())]


class CloudGroupTemplatesCombo(QtWidgets.QComboBox):
    """
    Combo box for listing the available templates/images in the service provider
    """
    def __init__(self, parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self._templates = {}

    def refresh(self, cloud_group):
        """
        :type cloud_group: opencue.cloud.api.CloudInstanceGroup
        :param cloud_group: Cloud group object used to query the list of image templates and populate the combobox with
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


class GoogleTemplateWidget(QtWidgets.QWidget):
    """
    Widget subclass for google templates selection
    """

    def __init__(self, google_manager, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        google_layout = QtWidgets.QGridLayout(self)
        google_layout.setSpacing(10)
        self.parent = parent

        self.google_manager_object = google_manager[0]
        google_layout.addWidget(QtWidgets.QLabel("Select Template/Image: ", self), 0, 0, 1, 2)
        self.templates_dropdown = CloudGroupTemplatesCombo(self)
        google_layout.addWidget(self.templates_dropdown, 0, 2, 1, 2)

        self.templates_dropdown.refresh(self.google_manager_object)

        google_layout.addWidget(QtWidgets.QLabel("Group Details: ", self), 2, 0, 1, 2)

        google_layout.addWidget(QtWidgets.QLabel("Name of group: ", self), 4, 0, 1, 1)
        self.__groupname_text_input = QtWidgets.QLineEdit()
        google_layout.addWidget(self.__groupname_text_input, 4, 2, 1, 2)

        google_layout.addWidget(QtWidgets.QLabel("Number of Instances: ", self), 5, 0, 1, 1)
        self.__number_of_instances = QtWidgets.QLineEdit()
        google_layout.addWidget(self.__number_of_instances, 5, 2, 1, 2)

        self.__btnGoogleCreateGroup = QtWidgets.QPushButton("Create Group")
        google_layout.addWidget(self.__btnGoogleCreateGroup, 6, 1, 1, 2)

        self.__btnGoogleCreateGroup.clicked.connect(self.create_google_group)

    def create_google_group(self):
        group_name = self.__groupname_text_input.text()
        instances = self.__number_of_instances.text()
        template = self.templates_dropdown.get_template_data()
        try:
            request = self.google_manager_object.create_managed_group(name=group_name, size=instances,
                                                                      template=template)
            if request:
                self.parent.close()
        except opencue.cloud.api.CloudProviderException as e:
            cuegui.Utils.showErrorMessageBox(text="{} {} request error!".format(e.provider, e.error_code),
                                             detailedText=e.message)


class AzureTemplateWidget(QtWidgets.QWidget):
    """
    Widget subclass for azure templates selection
    """

    def __init__(self, azure_manager, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        azure_layout = QtWidgets.QGridLayout(self)
        azure_layout.setSpacing(10)
        self.image_definition_data = {}
        self.parent = parent

        self.azure_manager_object = azure_manager[0]
        azure_layout.addWidget(QtWidgets.QLabel("Select Gallery: ", self), 0, 0, 1, 2)
        self.galleries_dropdown = QtWidgets.QComboBox(self)
        azure_layout.addWidget(self.galleries_dropdown, 0, 2, 1, 2)

        azure_layout.addWidget(QtWidgets.QLabel("Select Image Definition: ", self), 1, 0, 1, 2)
        self.images_dropdown = QtWidgets.QComboBox(self)
        azure_layout.addWidget(self.images_dropdown, 1, 2, 1, 2)

        #TODO: Ask for SKU as well?

        azure_layout.addWidget(QtWidgets.QLabel("Group Details: ", self), 3, 0, 1, 2)

        azure_layout.addWidget(QtWidgets.QLabel("Name of group: ", self), 5, 0, 1, 1)
        self.__groupname_text_input = QtWidgets.QLineEdit()
        azure_layout.addWidget(self.__groupname_text_input, 5, 2, 1, 2)

        azure_layout.addWidget(QtWidgets.QLabel("Number of Instances: ", self), 6, 0, 1, 1)
        self.__number_of_instances = QtWidgets.QLineEdit()
        azure_layout.addWidget(self.__number_of_instances, 6, 2, 1, 2)

        self.__btnAzureCreateGroup = QtWidgets.QPushButton("Create Group")
        azure_layout.addWidget(self.__btnAzureCreateGroup, 7, 1, 1, 2)

        self.populate_gallery_dropdown()
        self.list_image_definitions()
        self.galleries_dropdown.currentIndexChanged.connect(self.list_image_definitions)

        self.__btnAzureCreateGroup.clicked.connect(self.create_azure_group)

    def populate_gallery_dropdown(self):
        for gallery in self.azure_manager_object.list_galleries_in_resource_group():
            self.galleries_dropdown.addItem(gallery.name)

    def list_image_definitions(self):
        self.image_definition_data = {}
        for image in self.azure_manager_object.list_image_definitions_by_gallery(self.galleries_dropdown.currentText()):
            self.images_dropdown.addItem(image.name)
            self.image_definition_data[image.name] = image

    def create_azure_group(self):
        group_name = self.__groupname_text_input.text()
        instances = self.__number_of_instances.text()
        image_definition = self.image_definition_data[self.images_dropdown.currentText()]

        try:
            request = self.azure_manager_object.create_managed_group(name=group_name, size=instances,
                                                                     template=image_definition)
            if request:
                self.parent.close()
        except opencue.cloud.api.CloudProviderException as e:
            cuegui.Utils.showErrorMessageBox(text="{} {} request error!".format(e.provider, e.error_code),
                                             detailedText=e.message)


class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)

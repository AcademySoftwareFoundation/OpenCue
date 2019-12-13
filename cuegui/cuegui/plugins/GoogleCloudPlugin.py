#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import json
import requests
import subprocess

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.AbstractDockWidget
import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions

import opencue

logger = cuegui.Logger.getLogger(__file__)


PLUGIN_NAME = "GoogleCloud"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to control Google Cloud resource groups"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "GoogleCloudDockWidget"
UPDATE_INTERVAL = 60  # 60 seconds

class GoogleCloudDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        super(GoogleCloudDockWidget, self).__init__(parent, PLUGIN_NAME)
    
        self.__googleCloudWidget = GoogleCloudWidget(self)
    
        self.layout().addWidget(self.__googleCloudWidget)
    
        self.pluginRegisterSettings([("columnVisibility",
                                      self.__googleCloudWidget.getColumnVisibility,
                                      self.__googleCloudWidget.setColumnVisibility)])


class GoogleCloudWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(GoogleCloudWidget, self).__init__(parent)
        
        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddWorkerPool = QtWidgets.QPushButton("Create Worker Pool", self)
        self.__btnAddWorkerPool.setFocusPolicy(QtCore.Qt.NoFocus)
        
        self.__monitorWorkerPools = GoogleCloudTreeWidget(self)
        
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__btnAddWorkerPool, 0, 3)
        layout.addWidget(self.__btnRefresh, 0, 2)
        layout.addWidget(self.__monitorWorkerPools, 2, 0, 3, 4)
        
        self.__btnAddWorkerPool.clicked.connect(self.__addWorkerPool)
        self.__btnRefresh.clicked.connect(self.updateSoon)
        
        self.__menuActions = cuegui.MenuActions.MenuActions(self, self.updateSoon, list)
    
    def updateSoon(self):
        self.__monitorWorkerPools._update()
    
    def __addWorkerPool(self):
        GoogleCloudResourceManagement.getWorkerPool('gdenton-test')
        # GoogleCloudResourceManagement.createWorkerPool(id='gdenton-test',
        #                                                instance_template='doesnotexist',
        #                                                min_size=0,
        #                                                max_size=0,
        #                                                shutdown_policy='BY_PRIORITY')
        self.updateSoon()
  
    def getColumnVisibility(self):
        return self.__monitorWorkerPools.getColumnVisibility()
    
    def setColumnVisibility(self, settings):
        self.__monitorWorkerPools.setColumnVisibility(settings)
  

class GoogleCloudTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_LIMIT)
        self.addColumn("Worker Pool", 90, id=1,
                       data=lambda pool: pool.name())
        self.addColumn("Min Size", 80, id=2,
                       data=lambda pool: ("%d" % pool.maxValue()),
                       sort=lambda pool: pool.maxValue())
        self.addColumn("Max Size", 80, id=3,
                       data=lambda pool: ("%d" % pool.maxValue()),
                       sort=lambda pool: pool.maxValue())
        self.addColumn("Running", 80, id=4,
                       data=lambda pool: ("%d" % pool.currentRunning()),
                       sort=lambda pool: pool.currentRunning())
        self.addColumn("Shutdown Policy", 80, id=5,
                       data=lambda pool: "BY_PRIORITY",
                       sort=lambda pool: "BY_PRIORITY")
        
        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)
        
        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)
        
        self.itemClicked.connect(self.__itemSingleClickedToDouble)
        QtGui.qApp.facility_changed.connect(self.__facilityChanged)
        
        self.setUpdateInterval(UPDATE_INTERVAL)
    
    def __facilityChanged(self):
        """Called when the facility is changed"""
        self.removeAllItems()
        self._update()
    
    def __itemSingleClickedToDouble(self, item, col):
        """Called when an item is clicked on. Causes single clicks to be treated
        as double clicks.
        @type  item: QTreeWidgetItem
        @param item: The item single clicked on
        @type  col: int
        @param col: Column number single clicked on"""
        self.itemDoubleClicked.emit(item, col)
    
    def _createItem(self, object):
        """Creates and returns the proper item"""
        item = GoogleCloudWidgetItem(object, self)
        return item
    
    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            # pools = GoogleCloudResourceManagement.listWorkerPools()
            return opencue.api.getLimits()
        except Exception as e:
            logger.critical(e)
            return []
    
    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.limits().addAction(menu, "editMaxValue")
        menu.addSeparator()
        self.__menuActions.limits().addAction(menu, "delete")
        self.__menuActions.limits().addAction(menu, "rename")
        menu.exec_(QtCore.QPoint(e.globalX(), e.globalY()))


class GoogleCloudWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    def __init__(self, object, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_LIMIT, object, parent)



class GoogleCloudResourceManagement(object):
  
    base_url = 'https://autopush-mediarendering.sandbox.googleapis.com'
    project_id = '271850535195'
    region = 'global'
    version = 'v1alpha1'

    api_url = '{base_url}/{version}/projects/{project}/locations/{region}'.format(
        base_url=base_url,
        project=project_id,
        region=region,
        version=version)

    @classmethod
    def createWorkerPool(cls, id, instance_template, min_size, max_size, shutdown_policy):
        create_url = '{url}/workerPools?worker_pool_id={id}'.format(url=cls.api_url, id=id)
        data = {
            'instance_template': instance_template,
            'scaling_policy': {
                'min_size': min_size,
                'max_size': max_size,
                'shutdown_policy': shutdown_policy}}
        response = requests.post(create_url, data=json.dumps(data), headers=cls.getHeaders())
        return response

    @classmethod
    def getHeaders(cls):
        cmd = ['gcloud', 'auth', 'application-default', 'print-access-token']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        results = proc.communicate()
        auth_token = results[0].split('\n')[0]
        headers = {'Authorization': 'Bearer "{token}"'.format(token=auth_token)}
        return headers
    
    @classmethod
    def getWorkerPool(cls, worker_pool_id):
        get_url = '{url}/workerPools/{id}'.format(url=cls.api_url, id=worker_pool_id)
        response = requests.get(get_url, headers=cls.getHeaders())
        print(response.status_code)
        print(response.content)
        
    @classmethod
    def listWorkerPools(cls):
        get_url = '{url}/workerPools'.format(url=cls.api_url)
        response = requests.get(get_url, headers=cls.getHeaders())
        print(response.status_code)
        print(response.content)

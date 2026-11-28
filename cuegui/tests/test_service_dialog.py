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


"""Tests for cuegui.ServiceDialog."""


import unittest

import mock
import qtpy.QtCore

import opencue_proto.service_pb2
import opencue.wrappers.service

import cuegui.ServiceDialog
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class ServiceFormTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.form = cuegui.ServiceDialog.ServiceForm()

    @staticmethod
    def __service(email_on_failing):
        return opencue.wrappers.service.Service(
            opencue_proto.service_pb2.Service(
                id='service-id', name='shell', min_cores=100, max_cores=100,
                min_memory_increase=2097152, email_on_failing=email_on_failing))

    def __save(self):
        """Saves the form and returns the service it emitted."""
        saved = []
        self.form.saved.connect(saved.append)
        self.form.save()
        return saved[0]

    def test_setServiceShowsEmailOnFailing(self):
        self.form.setService(self.__service(True))
        self.assertTrue(self.form.email_on_failing.isChecked())

        self.form.setService(self.__service(False))
        self.assertFalse(self.form.email_on_failing.isChecked())

    def test_saveKeepsEmailOnFailing(self):
        self.form.setService(self.__service(True))

        self.assertTrue(self.__save().emailOnFailing())

    def test_saveSetsEmailOnFailing(self):
        self.form.setService(self.__service(False))
        self.form.email_on_failing.setChecked(True)

        self.assertTrue(self.__save().emailOnFailing())

    def test_newServiceHasEmailOnFailingOff(self):
        self.form.setService(self.__service(True))
        self.form.new()
        self.form.name.setText('newservice')

        self.assertFalse(self.form.email_on_failing.isChecked())
        self.assertFalse(self.__save().emailOnFailing())


if __name__ == '__main__':
    unittest.main()

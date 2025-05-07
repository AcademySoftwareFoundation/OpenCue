#  Copyright (c) OpenCue Project Authors
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


"""Tests for cuegui.DependWizard."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtWidgets
import qtpy.QtTest

import opencue_proto.job_pb2
import opencue.wrappers.frame
import opencue.wrappers.layer
import opencue.wrappers.job

import cuegui.DependWizard
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class DependWizardTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        self.parentWidget = qtpy.QtWidgets.QWidget()

    @mock.patch('cuegui.Cuedepend.createJobOnLayerDepend')
    @mock.patch('opencue.api.findJob')
    @mock.patch('opencue.api.getJobNames')
    def test_job_on_layer(self, get_job_names_mock, find_job_mock, create_depend_mock):
        show_name = 'arbitraryshow'
        shot_name = 'sh01'
        user_name = 'arbitraryuser'
        job_prefix = '%s-%s-%s' % (show_name, shot_name, user_name)
        job_dependon_name = '%s_dependon' % job_prefix
        job_depender_name = '%s_depender' % job_prefix
        layer_dependon_name = 'arbitraryLayerName'

        # Create depend-on job with one layer
        job_dependon = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=job_dependon_name, name=job_dependon_name,
                                               show='arbitraryshow'))
        layer_dependon = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name=layer_dependon_name))
        job_dependon.getLayers = lambda: [layer_dependon]

        # Create depend-er job, no layers needed
        job_depender = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=job_depender_name, name=job_depender_name,
                                               show='arbitraryshow'))

        # API mocks to allow wizard to load job information
        get_job_names_mock.return_value = [job_dependon_name, job_depender_name]
        find_job_mock.side_effect = lambda name: job_dependon if name == job_dependon_name else None

        # Create the Depend Wizard
        depend_wizard = cuegui.DependWizard.DependWizard(self.parentWidget, [job_depender])

        # Select job-on-layer then go to next page
        depend_type_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_DEPEND_TYPE)
        jol_option = depend_type_page._PageDependType__options[cuegui.DependWizard.JOL]
        jol_option.setChecked(True)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_ONJOB, depend_wizard.currentId())

        # Ensure the depend-on job is the only one selected, then go to next page
        select_on_job_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_ONJOB)
        job_list = select_on_job_page._PageSelectOnJob__jobList
        for job_list_index in range(job_list.count()):
            if job_list.item(job_list_index).text() == job_dependon_name:
                job_list.item(job_list_index).setSelected(True)
            else:
                job_list.item(job_list_index).setSelected(False)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_ONLAYER, depend_wizard.currentId())

        # Ensure the depend-on layer is the only one selected, then go to the next page
        select_on_layer_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_ONLAYER)
        layer_list = select_on_layer_page._PageSelectOnLayer__onLayerList
        for layer_list_index in range(layer_list.count()):
            if layer_list.item(layer_list_index).text() == layer_dependon_name:
                layer_list.item(layer_list_index).setSelected(True)
            else:
                layer_list.item(layer_list_index).setSelected(False)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_CONFIRMATION, depend_wizard.currentId())

        # Proceed past confirmation screen to create the depend
        depend_wizard.next()

        create_depend_mock.assert_called_with(
            job_depender_name, job_dependon_name, layer_dependon_name)

    @mock.patch('cuegui.Cuedepend.createLayerOnJobDepend')
    @mock.patch('opencue.api.findJob')
    @mock.patch('opencue.api.getJobNames')
    def test_layer_on_job(self, get_job_names_mock, find_job_mock, create_depend_mock):
        show_name = 'arbitraryshow'
        shot_name = 'sh01'
        user_name = 'arbitraryuser'
        job_prefix = '%s-%s-%s' % (show_name, shot_name, user_name)
        job_dependon_name = '%s_dependon' % job_prefix
        job_depender_name = '%s_depender' % job_prefix
        layer_depender_name = 'arbitraryLayerName'

        # Create depend-on job, no layers needed
        job_dependon = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=job_dependon_name, name=job_dependon_name,
                                               show='arbitraryshow'))

        # Create depend-er job with one layer
        job_depender = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=job_depender_name, name=job_depender_name,
                                               show='arbitraryshow'))
        layer_depender = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name=layer_depender_name))
        job_depender.getLayers = lambda: [layer_depender]

        # API mocks to allow wizard to load job information
        get_job_names_mock.return_value = [job_dependon_name, job_depender_name]
        find_job_mock.side_effect = lambda name: job_dependon if name == job_dependon_name else None

        # Create the Depend Wizard
        depend_wizard = cuegui.DependWizard.DependWizard(self.parentWidget, [job_depender])

        # Select layer-on-job then go to next page
        depend_type_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_DEPEND_TYPE)
        loj_option = depend_type_page._PageDependType__options[cuegui.DependWizard.LOJ]
        loj_option.setChecked(True)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_JOB_LAYER, depend_wizard.currentId())

        # Ensure the depend-er layer is the only one selected, then go to next page
        select_job_layer_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_JOB_LAYER)
        layer_list = select_job_layer_page._PageSelectLayer__layerList
        for layer_list_index in range(layer_list.count()):
            if layer_list.item(layer_list_index).text() == layer_depender_name:
                layer_list.item(layer_list_index).setSelected(True)
            else:
                layer_list.item(layer_list_index).setSelected(False)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_ONJOB, depend_wizard.currentId())

        # Ensure the depend-on job is the only one selected, then go to next page
        select_on_job_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_ONJOB)
        job_list = select_on_job_page._PageSelectOnJob__jobList
        for job_list_index in range(job_list.count()):
            if job_list.item(job_list_index).text() == job_dependon_name:
                job_list.item(job_list_index).setSelected(True)
            else:
                job_list.item(job_list_index).setSelected(False)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_CONFIRMATION, depend_wizard.currentId())

        # Proceed past confirmation screen to create the depend
        depend_wizard.next()

        create_depend_mock.assert_called_with(
            job_depender_name, layer_depender_name, job_dependon_name)

    @mock.patch('cuegui.Cuedepend.createFrameOnFrameDepend')
    @mock.patch('opencue.api.findJob')
    @mock.patch('opencue.api.getJobNames')
    def test_frame_on_frame(self, get_job_names_mock, find_job_mock, create_depend_mock):
        show_name = 'arbitraryshow'
        shot_name = 'sh01'
        user_name = 'arbitraryuser'
        job_prefix = '%s-%s-%s' % (show_name, shot_name, user_name)
        job_dependon_name = '%s_dependon' % job_prefix
        layer_dependon_name = 'layerDependonName'
        frame_dependon_num = 1
        job_depender_name = '%s_depender' % job_prefix
        layer_depender_name = 'layerDependerName'
        frame_depender_name = '0040-%s' % layer_depender_name
        frame_depender_num = 40

        # Create depend-on job with one layer, no frames needed (frame number only is used)
        job_dependon = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=job_dependon_name, name=job_dependon_name,
                                               show='arbitraryshow'))
        layer_dependon = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name=layer_dependon_name))
        job_dependon.getLayers = lambda: [layer_dependon]

        # Create depend-er job with one layer and one frame
        job_depender = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(id=job_depender_name, name=job_depender_name,
                                               show='arbitraryshow'))
        layer_depender = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name=layer_depender_name))
        frame_depender = opencue.wrappers.frame.Frame(
            opencue_proto.job_pb2.Frame(
                id='arbitrary-frame-id', name=frame_depender_name, layer_name=layer_depender_name,
                number=frame_depender_num))

        # API mocks to allow wizard to load job information
        get_job_names_mock.return_value = [job_dependon_name, job_depender_name]
        find_job_mock.side_effect = lambda name: job_dependon if name == job_dependon_name else None

        # Create the Depend Wizard
        depend_wizard = cuegui.DependWizard.DependWizard(
            self.parentWidget, [job_depender], layers=[layer_depender], frames=[frame_depender])

        # Select frame-on-frame then go to next page
        depend_type_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_DEPEND_TYPE)
        loj_option = depend_type_page._PageDependType__options[cuegui.DependWizard.FOF]
        loj_option.setChecked(True)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_ONJOB, depend_wizard.currentId())

        # Ensure the depend-on job is the only one selected, then go to next page
        select_on_job_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_ONJOB)
        job_list = select_on_job_page._PageSelectOnJob__jobList
        for job_list_index in range(job_list.count()):
            if job_list.item(job_list_index).text() == job_dependon_name:
                job_list.item(job_list_index).setSelected(True)
            else:
                job_list.item(job_list_index).setSelected(False)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_ONLAYER, depend_wizard.currentId())

        # Ensure the depend-on layer is the only one selected, then go to the next page
        select_on_layer_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_ONLAYER)
        layer_list = select_on_layer_page._PageSelectOnLayer__onLayerList
        for layer_list_index in range(layer_list.count()):
            if layer_list.item(layer_list_index).text() == layer_dependon_name:
                layer_list.item(layer_list_index).setSelected(True)
            else:
                layer_list.item(layer_list_index).setSelected(False)
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_SELECT_ONFRAME, depend_wizard.currentId())

        # Input the depend-on frame number as the depend-on frame, then go to the next page
        select_on_frame_page = depend_wizard.page(cuegui.DependWizard.PAGE_SELECT_ONFRAME)
        frame_field = select_on_frame_page._PageSelectOnFrame__frame
        frame_field.setText(str(frame_dependon_num))
        depend_wizard.next()
        self.assertEqual(cuegui.DependWizard.PAGE_CONFIRMATION, depend_wizard.currentId())

        # Proceed past confirmation screen to create the depend
        depend_wizard.next()

        create_depend_mock.assert_called_with(
            job_depender_name, layer_depender_name, frame_depender_num, job_dependon_name,
            layer_dependon_name, frame_dependon_num)


if __name__ == '__main__':
    unittest.main()

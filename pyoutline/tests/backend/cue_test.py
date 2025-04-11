#!/usr/bin/env python

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
Tests for the outline.backend.cue module.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest
import xml.etree.ElementTree as ET

import mock

import opencue.compiled_proto.job_pb2
import opencue.wrappers.job

import outline
import outline.backend.cue
import outline.cuerun
from .. import test_utils


SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
TEST_USER = 'test-user'


class SerializeTest(unittest.TestCase):
    def testSerializeShellOutline(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')

        outline.config.set('outline', 'home', '/opencue/outline')
        outline.config.set('outline', 'user_dir', '/tmp/opencue/user')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)

        outlineXml = ET.fromstring(outline.backend.cue.serialize(launcher))

        self.assertEqual('spec', outlineXml.tag)
        self.assertEqual(1, len(outlineXml.findall('facility')))
        self.assertEqual('local', outlineXml.find('facility').text)
        self.assertEqual(1, len(outlineXml.findall('show')))
        self.assertEqual('testing', outlineXml.find('show').text)
        self.assertEqual(1, len(outlineXml.findall('shot')))
        self.assertEqual('default', outlineXml.find('shot').text)
        self.assertEqual(1, len(outlineXml.findall('user')))
        self.assertEqual(TEST_USER, outlineXml.find('user').text)
        self.assertEqual(1, len(outlineXml.findall('job')))
        job = outlineXml.find('job')
        self.assertEqual('shell', job.get('name'))
        self.assertEqual(1, len(job.findall('env')))
        self.assertEqual(0, len(list(job.find('env'))))
        self.assertEqual(1, len(job.findall('layers')))
        self.assertEqual(1, len(job.find('layers').findall('layer')))
        layer = job.find('layers').find('layer')
        self.assertEqual('cmd', layer.get('name'))
        self.assertEqual('Render', layer.get('type'))
        self.assertEqual(1, len(layer.findall('cmd')))
        self.assertEqual(
            '/opencue/outline/wrappers/opencue_wrap_frame '
            '/tmp/opencue/user '
            '/opencue/outline/bin/pycuerun '
            '{scripts_dir}/shell.outline '
            '-e #IFRAME#-cmd '
            '--version latest '
            '--repos  '
            '--debug'.format(scripts_dir=SCRIPTS_DIR), layer.find('cmd').text)
        self.assertEqual(1, len(layer.findall('range')))
        self.assertEqual('1000-1000', layer.find('range').text)
        self.assertEqual(1, len(layer.findall('chunk')))
        self.assertEqual('1', layer.find('chunk').text)
        self.assertEqual(1, len(layer.findall('services')))
        self.assertEqual(1, len(layer.find('services').findall('service')))
        self.assertEqual('shell', layer.find('services').find('service').text)
        self.assertEqual(1, len(outlineXml.findall('depends')))
        self.assertEqual(0, len(list(outlineXml.find('depends'))))


class CoresTest(unittest.TestCase):
    def setUp(self):
        # Ensure to reset current
        outline.Outline.current = None

    def create(self):
        ol = outline.Outline()
        layer = outline.Layer("test")
        ol.add_layer(layer)
        return ol, layer

    def assertCoresOverride(self, ol, v):
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        outlineXml = ET.fromstring(outline.backend.cue.serialize(launcher))
        job = outlineXml.find('job')
        layer = job.find('layers').find('layer')
        self.assertEqual(v, layer.find('cores').text)

    def testCores(self):
        ol, layer = self.create()
        layer.set_arg("cores", 42)
        self.assertCoresOverride(ol, "42.0")

    def testThreads(self):
        ol, layer = self.create()
        layer.set_arg("threads", 4)
        self.assertCoresOverride(ol, "4.0")

    def testCoresAndThreads(self):
        ol, layer = self.create()
        layer.set_arg("cores", 8)
        layer.set_arg("threads", 4)
        # cores overrides threads
        self.assertCoresOverride(ol, "8.0")

    def testNoCoreOverride(self):
        ol, layer = self.create()
        layer.set_arg("cores", None)

        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        outlineXml = ET.fromstring(outline.backend.cue.serialize(launcher))
        job = outlineXml.find('job')
        layer = job.find('layers').find('layer')
        self.assertIsNone(layer.find('cores'))


class BuildCommandTest(unittest.TestCase):
    def setUp(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        outline.config.set('outline', 'home', '')
        outline.config.set('outline', 'user_dir', '')
        self.ol = outline.load_outline(path)
        self.launcher = outline.cuerun.OutlineLauncher(self.ol, user=TEST_USER)
        self.layer = self.ol.get_layer('cmd')

    def testBuildShellCommand(self):
        self.assertEqual(
            [
                '/wrappers/opencue_wrap_frame', '', '/bin/pycuerun',
                '%s/shell.outline -e #IFRAME#-cmd' % SCRIPTS_DIR,
                '--version latest', '--repos ', '--debug',
            ],
            outline.backend.cue.build_command(self.launcher, self.layer))

    def testBuildCommandWithStrace(self):
        self.layer.set_arg('strace', True)
        self.layer.set_arg('setshot', False)

        with test_utils.TemporarySessionDirectory():
            self.ol.setup()

            self.assertEqual(
                [
                    'strace', '-ttt', '-T', '-e', 'open,stat', '-f', '-o',
                    '%s/strace.log' % self.ol.get_session().get_path(self.layer),
                    '/wrappers/opencue_wrap_frame_no_ss', '', '/bin/pycuerun',
                    '%s -e #IFRAME#-cmd' % self.ol.get_path(),
                    '--version latest', '--repos ', '--debug',
                ],
                outline.backend.cue.build_command(self.launcher, self.layer))

    def testBuildCommandWithCustomWrapper(self):
        devUser = 'foo-user'
        wrapperPath = '/fake/wrapper'
        self.launcher.set_flag('dev', True)
        self.launcher.set_flag('devuser', devUser)
        self.layer.set_arg('wrapper', wrapperPath)

        self.assertEqual(
            [
                wrapperPath, '', '/bin/pycuerun',
                '%s/shell.outline -e #IFRAME#-cmd' % SCRIPTS_DIR,
                '--version latest', '--repos ', '--debug', '--dev',
                '--dev-user %s' % devUser,
            ],
            outline.backend.cue.build_command(self.launcher, self.layer))


class LaunchTest(unittest.TestCase):

    def setUp(self):
        self.job_wait_period_original = outline.backend.cue.JOB_WAIT_PERIOD_SEC
        outline.backend.cue.JOB_WAIT_PERIOD_SEC = .1

    def tearDown(self):
        outline.backend.cue.JOB_WAIT_PERIOD_SEC = self.job_wait_period_original

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    @mock.patch('opencue.Cuebot.setHosts')
    @mock.patch('opencue.api.launchSpecAndWait')
    def testLaunch(self, launchSpecAndWaitMock, setHostsMock):
        launchSpecAndWaitMock.return_value = [opencue.wrappers.job.Job()]
        serverName = 'foo-server'
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        launcher.set_flag('server', serverName)
        serializedXml = launcher.serialize(use_pycuerun=True)

        outline.backend.cue.launch(launcher)

        launchSpecAndWaitMock.assert_called_with(serializedXml)
        setHostsMock.assert_called_with([serverName])

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    @mock.patch('opencue.api.isJobPending')
    @mock.patch('opencue.api.launchSpecAndWait')
    def testLaunchAndWait(self, launchSpecAndWaitMock, isJobPendingMock):
        jobName = 'some-job'
        launchSpecAndWaitMock.return_value = [
            opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=jobName))]
        # Trigger one iteration of the wait loop.
        isJobPendingMock.side_effect = [True, False]
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        launcher.set_flag('wait', True)
        serializedXml = launcher.serialize(use_pycuerun=True)

        outline.backend.cue.launch(launcher)

        launchSpecAndWaitMock.assert_called_with(serializedXml)
        isJobPendingMock.assert_has_calls([mock.call(jobName), mock.call(jobName)])

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    @mock.patch('opencue.api.getJob')
    @mock.patch('opencue.api.launchSpecAndWait')
    def testLaunchAndTest(self, launchSpecAndWaitMock, getJobMock):
        jobName = 'another-job'
        launchSpecAndWaitMock.return_value = [
            opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=jobName))]
        getJobMock.return_value = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(name=jobName, state=opencue.api.job_pb2.FINISHED))

        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        launcher.set_flag('test', True)
        serializedXml = launcher.serialize(use_pycuerun=True)

        outline.backend.cue.launch(launcher)

        launchSpecAndWaitMock.assert_called_with(serializedXml)


if __name__ == '__main__':
    unittest.main()

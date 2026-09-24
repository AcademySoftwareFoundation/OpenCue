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
Tests for the outline_backend_rest module.
"""

import os
import unittest
import xml.etree.ElementTree as ET

import mock
import requests

import outline
import outline.cuerun
import outline.exception
import outline_backend_rest


SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
TEST_USER = 'test-user'
GATEWAY_URL = 'http://localhost:8080'


class SerializeTest(unittest.TestCase):
    def testSerializeShellOutline(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')

        outline.config.set('outline', 'home', '/opencue/outline')
        outline.config.set('outline', 'user_dir', '/tmp/opencue/user')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)

        outlineXml = ET.fromstring(outline_backend_rest.serialize(launcher))

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


class SerializeFrameRangeTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None

    def testLargeContiguousRangeIsCompactInSpec(self):
        ol = outline.Outline(name='maya_render', frame_range='1001-2301')
        layer = outline.Layer('defaultRenderLayer', range='1001-2301')
        ol.add_layer(layer)
        cleanup_layer = outline.Layer('Cleanup')
        ol.add_layer(cleanup_layer)

        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        outlineXml = ET.fromstring(outline_backend_rest.serialize(launcher))

        render_layer = next(
            layer_el for layer_el in outlineXml.find('job').find('layers').findall('layer')
            if layer_el.get('name') == 'defaultRenderLayer')
        range_text = render_layer.find('range').text

        self.assertEqual('1001-2301', range_text)
        self.assertLess(len(range_text), 4000)


class CoresTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def create(self):
        ol = outline.Outline()
        layer = outline.Layer("test")
        ol.add_layer(layer)
        return ol, layer

    def assertCoresOverride(self, ol, v):
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        outlineXml = ET.fromstring(outline_backend_rest.serialize(launcher))
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
        self.assertCoresOverride(ol, "8.0")

    def testNoCoreOverride(self):
        ol, layer = self.create()
        layer.set_arg("cores", None)

        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        outlineXml = ET.fromstring(outline_backend_rest.serialize(launcher))
        job = outlineXml.find('job')
        layer = job.find('layers').find('layer')
        self.assertIsNone(layer.find('cores'))


class LaunchTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None
        self.orig_job_wait_period = outline_backend_rest.JOB_WAIT_PERIOD_SEC
        outline_backend_rest.JOB_WAIT_PERIOD_SEC = 0.01

        outline.config.set('backend:rest', 'cuerest_gateway_url', GATEWAY_URL)
        outline.config.set('backend:rest', 'jwt_secret', 'secret-key')
        outline_backend_rest.CUEREST_GATEWAY_URL = GATEWAY_URL

    def tearDown(self):
        outline_backend_rest.JOB_WAIT_PERIOD_SEC = self.orig_job_wait_period

    @mock.patch('outline_backend_rest._get_restgateway_session')
    def testLaunch(self, getSessionMock):
        session = mock.MagicMock(spec=requests.Session)
        getSessionMock.return_value = session

        launch_resp = mock.MagicMock(spec=requests.Response)
        launch_resp.json.return_value = {
            'jobs': {
                'jobs': [{'id': 'job-123', 'name': 'shell'}]
            }
        }
        session.post.return_value = launch_resp

        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        serialized_xml = launcher.serialize(use_pycuerun=True)

        job = outline_backend_rest.launch(launcher)

        session.post.assert_called_once_with(
            f"{GATEWAY_URL}/job.JobInterface/LaunchSpecAndWait",
            json={"spec": serialized_xml},
            timeout=outline_backend_rest.TIMEOUT
        )
        self.assertEqual([{'id': 'job-123', 'name': 'shell'}], job)
        session.close.assert_called_once()

    @mock.patch('outline_backend_rest.wait')
    @mock.patch('outline_backend_rest._get_restgateway_session')
    def testLaunchAndWait(self, getSessionMock, waitMock):
        session = mock.MagicMock(spec=requests.Session)
        getSessionMock.return_value = session

        expected_job = {'id': 'job-123', 'name': 'shell'}
        launch_resp = mock.MagicMock(spec=requests.Response)
        launch_resp.json.return_value = {'jobs': {'jobs': [expected_job]}}
        session.post.return_value = launch_resp

        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        launcher.set_flag('wait', True)

        job = outline_backend_rest.launch(launcher)

        self.assertEqual([expected_job], job)
        waitMock.assert_called_once_with(expected_job)

    @mock.patch('outline_backend_rest.test')
    @mock.patch('outline_backend_rest._get_restgateway_session')
    def testLaunchAndTest(self, getSessionMock, testMock):
        session = mock.MagicMock(spec=requests.Session)
        getSessionMock.return_value = session

        expected_job = {'id': 'job-456', 'name': 'shell'}
        launch_resp = mock.MagicMock(spec=requests.Response)
        launch_resp.json.return_value = {'jobs': {'jobs': [expected_job]}}
        session.post.return_value = launch_resp

        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)
        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        launcher.set_flag('test', True)

        job = outline_backend_rest.launch(launcher)

        self.assertEqual([expected_job], job)
        testMock.assert_called_once_with(expected_job)

    @mock.patch('outline_backend_rest._get_restgateway_session')
    def testWait(self, getSessionMock):
        session = mock.MagicMock(spec=requests.Session)
        getSessionMock.return_value = session

        pending_resp = mock.MagicMock(spec=requests.Response)
        pending_resp.json.return_value = {
            'job': {
                'id': 'job-123',
                'state': 'RUNNING',
                'jobStats': {'succeededFrames': 5, 'totalFrames': 10}
            }
        }

        finished_resp = mock.MagicMock(spec=requests.Response)
        finished_resp.json.return_value = {
            'job': {
                'id': 'job-123',
                'state': 'FINISHED',
                'jobStats': {'succeededFrames': 10, 'totalFrames': 10}
            }
        }
        session.post.side_effect = [pending_resp, finished_resp]

        outline_backend_rest.wait({'id': 'job-123'})

        self.assertEqual(2, session.post.call_count)
        session.post.assert_called_with(
            f"{GATEWAY_URL}/job.JobInterface/GetJob",
            json={'id': 'job-123'},
            timeout=outline_backend_rest.TIMEOUT
        )
        session.close.assert_called_once()

    @mock.patch('outline_backend_rest.time.sleep', return_value=None)
    @mock.patch('outline_backend_rest._get_restgateway_session')
    def testTestSuccess(self, getSessionMock, sleepMock):
        session = mock.MagicMock(spec=requests.Session)
        getSessionMock.return_value = session

        resume_resp = mock.MagicMock(spec=requests.Response)
        getjob_resp = mock.MagicMock(spec=requests.Response)
        getjob_resp.status_code = 200
        getjob_resp.json.return_value = {
            'job': {
                'id': 'job-123',
                'state': 'FINISHED',
                'jobStats': {'deadFrames': 0,
                             'eatenFrames': 0,
                             'succeededFrames': 1,
                             'totalFrames': 1}
            }
        }
        kill_resp = mock.MagicMock(spec=requests.Response)

        session.post.side_effect = [resume_resp, getjob_resp, kill_resp]

        outline_backend_rest.test({'id': 'job-123', 'name': 'test-job'})

        calls = session.post.call_args_list
        self.assertEqual(f"{GATEWAY_URL}/job.JobInterface/Resume", calls[0][0][0])
        self.assertEqual(f"{GATEWAY_URL}/job.JobInterface/GetJob", calls[1][0][0])
        self.assertEqual(f"{GATEWAY_URL}/job.JobInterface/Kill", calls[2][0][0])
        session.close.assert_called_once()

    @mock.patch('outline_backend_rest.time.sleep', return_value=None)
    @mock.patch('outline_backend_rest._get_restgateway_session')
    def testTestDeadFramesRaisesException(self, getSessionMock, sleepMock):
        session = mock.MagicMock(spec=requests.Session)
        getSessionMock.return_value = session

        resume_resp = mock.MagicMock(spec=requests.Response)
        getjob_resp = mock.MagicMock(spec=requests.Response)
        getjob_resp.status_code = 200
        getjob_resp.json.return_value = {
            'job': {
                'id': 'job-123',
                'state': 'RUNNING',
                'jobStats': {'deadFrames': 1, 'eatenFrames': 0}
            }
        }
        kill_resp = mock.MagicMock(spec=requests.Response)

        session.post.side_effect = [resume_resp, getjob_resp, kill_resp]

        with self.assertRaises(outline.exception.OutlineException) as ctx:
            outline_backend_rest.test({'id': 'job-123', 'name': 'test-job'})

        self.assertIn('dead or eaten frames', str(ctx.exception))
        # Ensures kill was still invoked in finally block
        self.assertEqual(f"{GATEWAY_URL}/job.JobInterface/Kill",
                         session.post.call_args_list[-1][0][0])
        session.close.assert_called_once()


class BackendOverrideTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None
        self.orig_backend = outline.config.get('outline', 'backend')

    def tearDown(self):
        outline.config.set('outline', 'backend', self.orig_backend)

    def testOverrideBackend(self):
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)

        outline.config.set('outline', 'backend', 'rest')

        launcher = outline.cuerun.OutlineLauncher(ol)

        # Check that the backend configured on the launcher matches
        self.assertEqual('rest', launcher.get('backend'))
        self.assertEqual('rest', launcher.get_flag('backend'))

        # Check that the imported backend module resolves to the rest backend
        backend_module = outline.cuerun.import_backend_module(launcher.get('backend'))
        self.assertIs(outline_backend_rest, backend_module)


if __name__ == '__main__':
    unittest.main()

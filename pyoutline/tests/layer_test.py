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
Tests for the outline.layer module.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

# WARNING: Do not import builtins.str here as we do elsewhere in the code. Unit tests on Python 2
# need to preserve the existing Python 2 string type.
from builtins import range
import os
import sys
import unittest

import future.types
import mock

import outline
import outline.exception
import outline.io
import outline.layer
import outline.modules.shell

from . import test_utils


SCRIPTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'scripts')


class CompositeTest(unittest.TestCase):
    """
    Tests for a composite layer. Composite layers
    can contain multiple layers.
    """

    def setUp(self):
        self.ol = outline.Outline()
        self.layer = outline.layer.Layer("composite")
        self.ol.add_layer(self.layer)

        self.layer.add_child(outline.modules.shell.Shell("blah1", command=["ls", "-l"]))
        self.layer.add_child(outline.modules.shell.Shell("blah2", command=["ls", "-1"]))
        self.layer.add_child(outline.modules.shell.Shell("blah3", command=["ls"]))

        self.event = self.ol.get_layer("composite")

    @mock.patch('outline.layer.Layer.system')
    def test_execute(self, systemMock):
        """Run the execute method."""
        with test_utils.TemporarySessionDirectory():
            self.ol.setup()
            self.event.execute(1)

        systemMock.assert_has_calls([
            mock.call(['ls', '-l'], frame=1),
            mock.call(['ls', '-1'], frame=1),
            mock.call(['ls'], frame=1),
        ])


class ChunkingTest(unittest.TestCase):

    """Tests layer chunking."""

    def setUp(self):
        self.ol = outline.load_outline(os.path.join(SCRIPTS_DIR, 'shell.outline'))
        self.ol.set_frame_range("1-10")

        self.event = self.ol.get_layer("cmd")
        self.event.set_chunk_size(5)

    def test_get_local_frame_set(self):
        """
        Test to make sure that that the localFrameSet is
        being constructed properly.  The local frame set
        is the frame list a particular frame is responsible
        for executing on the cue.  When the chunk-size is
        greated then 1, the local frame set will contain
        more than a single frame.
        """
        with test_utils.TemporarySessionDirectory():
            self.ol.setup()
        self.assertEqual([1, 2, 3, 4, 5], self.event.get_local_frame_set(1).getAll())
        self.assertEqual([8, 9, 10], self.event.get_local_frame_set(8).getAll())


class RangeTests(unittest.TestCase):

    """Tests that the proper frame ranges are being resolved."""

    def setUp(self):
        self.ol = outline.load_outline(os.path.join(SCRIPTS_DIR, 'shell.outline'))

    def test_no_layer_range_no_job_range(self):
        # No layer range, no outline range defaults to a single frame.
        self.assertEqual('1000-1000', self.ol.get_layer('cmd').get_frame_range())
        self.assertEqual(None, self.ol.get_frame_range())

    def test_no_layer_range_job_range(self):
        self.ol.set_frame_range('1000-2000')

        # No layer range, no outline range defaults to a single frame.
        self.assertEqual('1000-2000', self.ol.get_layer('cmd').get_frame_range())
        self.assertEqual('1000-2000', self.ol.get_frame_range())

    def test_layer_range_no_job_range(self):
        self.ol.get_layer('cmd').set_frame_range('1000-2000')
        self.assertEqual('1000-2000', self.ol.get_layer('cmd').get_frame_range())
        self.assertEqual(None, self.ol.get_frame_range())

    def test_layer_range_job_range(self):
        self.ol.set_frame_range('1000-2000')
        self.ol.get_layer('cmd').set_frame_range('1000-2000')

        expectedFrameStr = ','.join([str(i) for i in range(1000, 2001)])
        self.assertEqual(expectedFrameStr, self.ol.get_layer('cmd').get_frame_range())
        self.assertEqual('1000-2000', self.ol.get_frame_range())

    def test_intersecting_range(self):
        self.ol.set_frame_range('1000-2000x8')
        self.ol.get_layer('cmd').set_frame_range('1000-2000')

        expectedFrameStr = ','.join([str(i) for i in range(1000, 2001, 8)])
        self.assertEqual(expectedFrameStr, self.ol.get_layer('cmd').get_frame_range())
        self.assertEqual('1000-2000x8', self.ol.get_frame_range())

    def test_intersecting_failure(self):
        self.ol.set_frame_range('1000-1010')
        self.ol.get_layer('cmd').set_frame_range('1100-1200')

        self.assertFalse(self.ol.get_layer('cmd').get_frame_range())


class LayerTest(unittest.TestCase):
    """Tests for outline layer."""

    def setUp(self):
        """Setup a basis event from a preset outline file."""
        outline.config.add_section('Shell')
        outline.config.set('Shell', 'foo', 'bar')
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        self.ol = outline.load_outline(path)
        self.ol.set_frame_range('1-10')
        self.ol.set_env('cue_test_01', 'foo')
        self.ol.set_env('cue_test_02', 'bar')
        self.layer = self.ol.get_layer('cmd')
        self.layer.set_env('cue_layer_01', 'layer-env-a')
        self.layer.set_env('cue_layer_02', 'layer-env-b')

    def tearDown(self):
        outline.config.remove_section('Shell')

    def test_name(self):
        """Test the name has been set properly."""
        self.assertEqual('cmd', self.layer.get_name())

    def test_to_string(self):
        """Tests to ensure __str__ returns the layer name."""
        self.assertEqual(self.layer.get_name(), str(self.layer))

    def test_get_set_args(self):
        """Test the argument getter/setter methods."""
        self.assertEqual(self.layer.get_arg('test1'), 1)
        self.assertEqual(self.layer.get_arg('test2'), 2)

        self.layer.set_arg('foo', 1)

        self.assertEqual(1, self.layer.get_arg('foo'))
        self.assertEqual(1, self.layer.get_arg('bar', 1))

        self.layer.set_default_arg('foo', 2)
        self.layer.set_default_arg('foo2', 2)
        self.assertEqual(1, self.layer.get_arg('foo'))
        self.assertEqual(2, self.layer.get_arg('foo2'))

    def test_invalid_type_args(self):
        """Test the interpolation of arg strings."""

        intArgName = 'some-int-arg'
        self.layer.require_arg(intArgName, int)
        self.assertRaises(
            outline.exception.LayerException, self.layer.set_arg, intArgName, 'some-string-val')
        self.layer.set_arg(intArgName, 872)

        if sys.version_info[0] >= 3:
            strArgName = 'some-str-arg'
            self.layer.require_arg(strArgName, str)
            self.assertRaises(
                outline.exception.LayerException, self.layer.set_arg, strArgName, dict())
            self.layer.set_arg(strArgName, 'py3-string')
        else:
            strArgName = 'some-str-arg'
            self.layer.require_arg(strArgName, str)
            self.assertRaises(
                outline.exception.LayerException, self.layer.set_arg, strArgName, dict())
            self.layer.set_arg(strArgName, 'standard-py2-string')
            self.layer.set_arg(strArgName, u'py2-unicode')
            self.layer.set_arg(strArgName, future.types.newstr('py3-string-backport'))

            newstrArgName = 'some-newstr-arg'
            self.layer.require_arg(newstrArgName, future.types.newstr)
            self.assertRaises(
                outline.exception.LayerException, self.layer.set_arg, newstrArgName, dict())
            self.layer.set_arg(newstrArgName, 'standard-py2-string')
            self.layer.set_arg(newstrArgName, u'py2-unicode')
            self.layer.set_arg(newstrArgName, future.types.newstr('py3-string-backport'))

    def test_require_arg(self):
        """
        Test required arguments.  Unset required args will
        throw a LayerException if they are not set before
        setup() is run.
        """
        self.layer.require_arg('bobofet')
        self.assertRaises(outline.exception.LayerException, self.layer.check_required_args)
        self.layer.set_arg('bobofet', 1)
        self.layer.check_required_args()

    def test_default_args(self):
        default_args = self.layer.get_default_args()

        self.assertEqual(
            {'chunk': 1, 'register': True, 'range': None, 'foo': 'bar'},
            default_args)

    def test_args_override(self):
        with test_utils.TemporarySessionDirectory():
            self.ol.setup()
            self.layer.put_data('args_override', {'arg_to_be_overridden': 'blah.blah'})

            self.layer.setup_args_override()

            self.assertEqual('blah.blah', self.layer.get_arg('arg_to_be_overridden'))

    def test_get_path(self):
        """Test that the layer session path is correct."""
        with test_utils.TemporarySessionDirectory():
            self.assertRaises(outline.exception.OutlineException, self.layer.get_path)
            self.ol.setup()
            expectedPath = '%s/layers/%s' % (
                self.ol.get_session().get_path(), self.layer.get_name())
            self.assertEqual(expectedPath, self.layer.get_path())

    def test_setup(self):
        """Test setting up the event for launch."""
        with test_utils.TemporarySessionDirectory():
            self.layer.setup()

    @mock.patch('outline.layer.Layer.system')
    def test_execute(self, systemMock):
        """Test execution of a frame."""
        os.environ = {}

        with test_utils.TemporarySessionDirectory():
            self.ol.setup()
            self.layer.execute(1)

            systemMock.assert_has_calls([mock.call(['ps', 'aux'], frame=1)])
            self.assertEqual('foo', os.environ['cue_test_01'])
            self.assertEqual('bar', os.environ['cue_test_02'])
            self.assertEqual('layer-env-a', os.environ['cue_layer_01'])
            self.assertEqual('layer-env-b', os.environ['cue_layer_02'])

    def test_get_set_frame_range(self):
        """Test getting/setting the frame range.  If the frame
        range is not set on a layer, then it should default to
        the outline frame range.
        """
        self.assertEqual(self.ol.get_frame_range(), self.layer.get_frame_range())
        self.layer.set_frame_range('1-10')
        self.assertEqual('1,2,3,4,5,6,7,8,9,10', self.layer.get_frame_range())

    def test_get_set_chunk_size(self):
        """Test get/set of chunk size."""
        self.layer.set_chunk_size(5)
        self.assertEqual(5, self.layer.get_chunk_size())

    def test_add_layer_during_setup(self):
        """Test to ensure that layers added during setup are serialized."""
        with test_utils.TemporarySessionDirectory():
            ol = outline.Outline('mr_hat')
            ol.add_layer(TestA('test_a'))
            ol.setup()

            ol_b = outline.load_outline(ol.get_session().get_file('outline.yaml'))
            # ensure the new layer was added
            self.assertTrue(ol_b.get_layer('test_b'))
            #  ensure that setup was actually run on the new layer
            self.assertTrue(ol_b.get_layer('test_b').is_setup)

    def test_after_init(self):
        ol = outline.Outline('after_init')
        ol.add_layer(TestAfterInit('test'))

        # Ensure after init was run,
        self.assertTrue(ol.get_layer('test').get_arg('after_init'))
        # Ensure that the layer has the right ol reference
        self.assertEqual(ol, ol.get_layer('test').get_outline())

    def test_after_init_current(self):
        ol = outline.Outline('after_init', current=True)
        TestAfterInit('test')

        # Ensure after init was run,
        self.assertTrue(ol.get_layer('test').get_arg('after_init'))
        # Ensure that the layer has the right ol reference
        self.assertEqual(ol, ol.get_layer('test').get_outline())

    def test_dependency_creation(self):
        with test_utils.TemporarySessionDirectory():
            outline.Outline.current = None
            ol = outline.Outline('after_init')
            ol.add_layer(TestAfterInit('test'))
            ol.add_layer(TestB('testb', require='test'))
            ol.setup()

            # check the depend was setup properly
            self.assertEqual(1, len(ol.get_layer('testb').get_depends()))

    def test_type_arg(self):
        """Test to ensure the type argument is handled properly."""
        outline.Outline.current = None
        t = TestA('test', type='Post')
        self.assertEqual('Post', t.get_type())

    def test_set_output_attribute(self):
        """Test setting an output attribute on all registered output."""
        t = TestA('test')
        t.add_output('node1', outline.io.Path('/tmp'))
        t.set_output_attribute('test', True)
        self.assertTrue(t.get_output('node1').get_attribute('test'))

    @mock.patch('outline.io.system')
    def test_system(self, systemMock):
        self.layer.system('arbitrary-command', ignore_error=True)

        systemMock.assert_called_with('arbitrary-command', True, None)

    def test_set_name(self):
        newLayerName = 'arbitrary-new-name'

        self.layer.set_name(newLayerName)

        self.assertEqual(newLayerName, self.layer.get_name())

        with test_utils.TemporarySessionDirectory():
            self.ol.setup()

            self.assertRaises(
                outline.exception.LayerException, self.layer.set_name, 'this-should-fail')


class OutputRegistrationTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None

    # TODO(bcipriano) Re-enable this test once FileSequence has a Python
    #  implementation. (Issue #242)
    def disabled__test_output_passing(self):
        """
        Test that output registered in a pre-process is serialized
        to a ol:outputs file in the render layer.
        """
        with test_utils.TemporarySessionDirectory():
            ol = outline.Outline("pre_test")

            # the render layer
            layer1 = TestA("test1")

            # the preprocess
            prelayer = outline.layer.LayerPreProcess(layer1)
            prelayer._execute = lambda frames: prelayer.add_output(
                "test", outline.io.FileSpec("/tmp/foo.#.exr"))

            # Add both to the outline
            ol.add_layer(layer1)
            ol.add_layer(prelayer)

            # setup for execute
            ol.setup()

            # now run the preprocess
            prelayer.execute(1000)

            # The file should exist.
            self.assertTrue(os.path.exists("%s/ol:outputs" % layer1.get_path()))

            # now run a single frame of the render layer and ensure that
            # the outputs are automatically loaded.
            layer1.execute(1000)
            self.assertEqual(1, len(layer1.get_outputs()))


class TestAfterInit(outline.layer.Layer):
    def __init__(self, name, **args):
        outline.layer.Layer.__init__(self, name, **args)

    def after_init(self, ol):
        self.set_arg("after_init", True)


class TestA(outline.layer.Layer):
    def __init__(self, name, **args):
        outline.layer.Layer.__init__(self, name, **args)

    def setup(self):
        self.get_outline().add_layer(TestB("test_b"))


class TestB(outline.layer.Layer):
    def __init__(self, name, **args):
        outline.layer.Layer.__init__(self, name, **args)
        self.is_setup = False

    def setup(self):
        self.is_setup = True


if __name__ == '__main__':
    unittest.main()

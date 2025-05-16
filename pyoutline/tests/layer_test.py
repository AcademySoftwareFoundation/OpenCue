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
import outline.layer
import outline.io
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
        self.layer = outline.Layer("composite")
        self.ol.add_layer(self.layer)

        self.layer.add_child(outline.modules.shell.Shell("blah1", command=["ls", "-l"]))
        self.layer.add_child(outline.modules.shell.Shell("blah2", command=["ls", "-1"]))
        self.layer.add_child(outline.modules.shell.Shell("blah3", command=["ls"]))

        self.event = self.ol.get_layer("composite")

    @mock.patch('outline.Layer.system')
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
            outline.LayerException, self.layer.set_arg, intArgName, 'some-string-val')
        self.layer.set_arg(intArgName, 872)

        if sys.version_info[0] >= 3:
            strArgName = 'some-str-arg'
            self.layer.require_arg(strArgName, str)
            self.assertRaises(
                outline.LayerException, self.layer.set_arg, strArgName, {})
            self.layer.set_arg(strArgName, 'py3-string')
        else:
            strArgName = 'some-str-arg'
            self.layer.require_arg(strArgName, str)
            self.assertRaises(
                outline.LayerException, self.layer.set_arg, strArgName, {})
            self.layer.set_arg(strArgName, 'standard-py2-string')
            self.layer.set_arg(strArgName, 'py2-unicode')
            self.layer.set_arg(strArgName, future.types.newstr('py3-string-backport'))

            newstrArgName = 'some-newstr-arg'
            self.layer.require_arg(newstrArgName, future.types.newstr)
            self.assertRaises(
                outline.LayerException, self.layer.set_arg, newstrArgName, {})
            self.layer.set_arg(newstrArgName, 'standard-py2-string')
            self.layer.set_arg(newstrArgName, 'py2-unicode')
            self.layer.set_arg(newstrArgName, future.types.newstr('py3-string-backport'))

    def test_require_arg(self):
        """
        Test required arguments.  Unset required args will
        throw a LayerException if they are not set before
        setup() is run.
        """
        self.layer.require_arg('bobofet')
        self.assertRaises(outline.LayerException, self.layer.check_required_args)
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
            self.assertRaises(outline.OutlineException, self.layer.get_path)
            self.ol.setup()
            expectedPath = '%s/layers/%s' % (
                self.ol.get_session().get_path(), self.layer.get_name())
            self.assertEqual(expectedPath, self.layer.get_path())

    def test_setup(self):
        """Test setting up the event for launch."""
        with test_utils.TemporarySessionDirectory():
            self.layer.setup()

    @mock.patch('outline.Layer.system')
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
                outline.LayerException, self.layer.set_name, 'this-should-fail')

    def test_should_fail_on_invalid_parent(self):
        invalid_object = 'some-string-object'

        self.assertRaises(outline.LayerException, self.layer.set_parent, invalid_object)

    def test_should_fail_on_invalid_child(self):
        invalid_object = 'some-string-object'

        self.assertRaises(outline.LayerException, self.layer.add_child, invalid_object)

    def test_should_add_event_listener(self):
        event_type = 'arbitrary-event-type'
        def callback(x):
            return x

        self.layer.add_event_listener(event_type, callback)

        self.assertEqual([callback], self.layer.get_event_handler().get_event_listeners(event_type))

    def test_should_fail_on_invalid_layer_type(self):
        invalid_layer_type = 'invalid-layer-type'

        self.assertRaises(outline.LayerException, self.layer.set_type, invalid_layer_type)

    def test_should_create_dependency_from_outline(self):
        with test_utils.TemporarySessionDirectory():
            outline.Outline.current = None
            ol = outline.Outline('after_init')
            ol.add_layer(TestAfterInit('test'))
            ol.add_layer(TestB('testb', require='test'))
            ol.setup()

            new_depend = ol.get_layer('testb').get_depends()[0]
            self.assertEqual('testb', new_depend.get_dependant_layer().get_name())
            self.assertEqual('test', new_depend.get_depend_on_layer().get_name())

    def test_should_create_dependency_from_layer(self):
        depend_on_layer = TestAfterInit('test')
        depend_er_layer = TestB('testb')

        depend_er_layer.depend_on(depend_on_layer)

        new_depend = depend_er_layer.get_depends()[0]
        self.assertEqual('testb', new_depend.get_dependant_layer().get_name())
        self.assertEqual('test', new_depend.get_depend_on_layer().get_name())

    def test_should_skip_duplicate_depend(self):
        depend_on_layer = TestAfterInit('test')
        depend_er_layer = TestB('testb')
        depend_er_layer.depend_on(depend_on_layer)
        num_depends = len(depend_er_layer.get_depends())

        depend_er_layer.depend_on(depend_on_layer)

        self.assertEqual(num_depends, len(depend_er_layer.get_depends()))

    def test_should_skip_depend_on_self(self):
        depend_layer = TestAfterInit('test')

        depend_layer.depend_on(depend_layer)

        self.assertEqual(0, len(depend_layer.get_depends()))

    def test_should_remove_depend(self):
        depend_on_layer = TestAfterInit('test')
        depend_er_layer = TestB('testb')
        depend_er_layer.depend_on(depend_on_layer)
        depend_to_remove = depend_er_layer.get_depends()[0]

        depend_er_layer.undepend(depend_to_remove)

        self.assertEqual(0, len(depend_er_layer.get_depends()))

    def test_should_get_dependents(self):
        with test_utils.TemporarySessionDirectory():
            depend_on_layer = TestAfterInit('test')
            depend_er_layer = TestB('testb', require='test')
            outline.Outline.current = None
            ol = outline.Outline('after_init')
            ol.add_layer(depend_on_layer)
            ol.add_layer(depend_er_layer)
            ol.setup()

            depend = depend_on_layer.get_dependents()[0]
            self.assertEqual('testb', depend.get_dependant_layer().get_name())
            self.assertEqual('test', depend.get_depend_on_layer().get_name())

    def test_should_add_inputs(self):
        layer = TestAfterInit('test')
        unnamed_input = outline.io.Path('/path/to/first/input')
        named_input = outline.io.Path('/path/to/second/input')
        bare_path = '/path/to/third/input'

        layer.add_input(None, unnamed_input)
        layer.add_input('named-input-name', named_input)
        layer.add_input('bare-path-name', bare_path)

        inputs = layer.get_inputs()
        self.assertEqual(unnamed_input, inputs['input0'])
        self.assertEqual(named_input, inputs['named-input-name'])
        self.assertEqual(bare_path, inputs['bare-path-name'].get_path())
        self.assertEqual(unnamed_input, layer.get_input('input0'))
        self.assertEqual(named_input, layer.get_input('named-input-name'))
        self.assertEqual(bare_path, layer.get_input('bare-path-name').get_path())

    def test_should_fail_on_duplicate_input(self):
        layer = TestAfterInit('test')
        input_to_add = outline.io.Path('/path/to/input')
        layer.add_input('input-name', input_to_add)

        self.assertRaises(outline.LayerException, layer.add_input, 'input-name', input_to_add)

    def test_should_check_input(self):
        layer = TestAfterInit('test')
        input_to_check = outline.io.Path('/path/to/input')
        input_to_check.set_attribute('checked', True)
        input_to_check.exists = mock.Mock()
        input_to_check.exists.return_value = True
        layer.add_input('input-name', input_to_check)

        layer.check_input()

        input_to_check.exists.assert_called()

    def test_should_skip_checking_input(self):
        layer = TestAfterInit('test')
        input_to_check = outline.io.Path('/path/to/input')
        input_to_check.set_attribute('checked', False)
        input_to_check.exists = mock.Mock()
        input_to_check.exists.return_value = True
        layer.add_input('input-name', input_to_check)

        layer.check_input()

        input_to_check.exists.assert_not_called()

    def test_should_fail_on_nonexistent_input(self):
        layer = TestAfterInit('test')
        input_to_check = outline.io.Path('/path/to/input')
        input_to_check.set_attribute('checked', True)
        input_to_check.exists = mock.Mock()
        input_to_check.exists.return_value = False
        layer.add_input('input-name', input_to_check)

        self.assertRaises(outline.LayerException, layer.check_input)

    def test_should_set_attribute_on_all_inputs(self):
        layer = TestAfterInit('test')
        input1 = outline.io.Path('/path/to/input')
        input2 = outline.io.Path('/path/to/another/input')
        layer.add_input('input-one', input1)
        layer.add_input('input-two', input2)
        attr_name = 'arbitrary-attribute-name'
        attr_val = 'arbitrary-attribute-value'

        layer.set_input_attribute(attr_name, attr_val)

        self.assertEqual(attr_val, input1.get_attribute(attr_name))
        self.assertEqual(attr_val, input2.get_attribute(attr_name))

    def test_should_add_outputs(self):
        layer = TestAfterInit('test')
        unnamed_output = outline.io.Path('/path/to/first/output')
        named_output = outline.io.Path('/path/to/second/output')
        bare_path = '/path/to/third/output'

        layer.add_output(None, unnamed_output)
        layer.add_output('named-output-name', named_output)
        layer.add_output('bare-path-name', bare_path)

        outputs = layer.get_outputs()
        self.assertEqual(unnamed_output, outputs['output0'])
        self.assertEqual(named_output, outputs['named-output-name'])
        self.assertEqual(bare_path, outputs['bare-path-name'].get_path())
        self.assertEqual(unnamed_output, layer.get_output('output0'))
        self.assertEqual(named_output, layer.get_output('named-output-name'))
        self.assertEqual(bare_path, layer.get_output('bare-path-name').get_path())

    def test_should_fail_on_duplicate_output(self):
        layer = TestAfterInit('test')
        output_to_add = outline.io.Path('/path/to/output')
        layer.add_output('output-name', output_to_add)

        self.assertRaises(outline.LayerException, layer.add_output, 'output-name', output_to_add)

    def test_should_check_output(self):
        layer = TestAfterInit('test')
        output_to_check = outline.io.Path('/path/to/output')
        output_to_check.set_attribute('checked', True)
        output_to_check.exists = mock.Mock()
        output_to_check.exists.return_value = True
        layer.add_output('output-name', output_to_check)

        layer.check_output()

        output_to_check.exists.assert_called()

    def test_should_skip_checking_output(self):
        layer = TestAfterInit('test')
        output_to_check = outline.io.Path('/path/to/output')
        output_to_check.set_attribute('checked', False)
        output_to_check.exists = mock.Mock()
        output_to_check.exists.return_value = True
        layer.add_output('output-name', output_to_check)

        layer.check_output()

        output_to_check.exists.assert_not_called()

    def test_should_fail_on_nonexistent_output(self):
        layer = TestAfterInit('test')
        output_to_check = outline.io.Path('/path/to/output')
        output_to_check.set_attribute('checked', True)
        output_to_check.exists = mock.Mock()
        output_to_check.exists.return_value = False
        layer.add_output('output-name', output_to_check)

        self.assertRaises(outline.LayerException, layer.check_output)

    def test_should_set_attribute_on_all_outputs(self):
        layer = TestAfterInit('test')
        output1 = outline.io.Path('/path/to/output')
        output2 = outline.io.Path('/path/to/another/output')
        layer.add_output('output-one', output1)
        layer.add_output('output-two', output2)
        attr_name = 'arbitrary-attribute-name'
        attr_val = 'arbitrary-attribute-value'

        layer.set_output_attribute(attr_name, attr_val)

        self.assertEqual(attr_val, output1.get_attribute(attr_name))
        self.assertEqual(attr_val, output1.get_attribute(attr_name))


class OutputRegistrationTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None

    def test_output_passing(self):
        """
        Test that output registered in a pre-process is serialized
        to a ol:outputs file in the render layer.
        """
        with test_utils.TemporarySessionDirectory():
            ol = outline.Outline("pre_test")

            # the render layer
            layer1 = TestA("test1")

            # the preprocess
            prelayer = outline.LayerPreProcess(layer1)
            prelayer._execute = lambda frames: prelayer.add_output(
                "test", outline.io.Path("/tmp/foo.#.exr"))

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


class FrameTests(unittest.TestCase):

    def test_should_return_first_frame_of_outline_range(self):
        """Test getting/setting the frame range.  If the frame
        range is not set on a layer, then it should default to
        the outline frame range.
        """
        frame_range = '55-65'
        outline.Outline.current = None
        ol = outline.Outline('after_init')
        ol.set_frame_range(frame_range)
        layer = outline.layer.Frame('layer-name')
        ol.add_layer(layer)
        self.assertEqual('55', layer.get_frame_range())

    def test_should_return_default_frame_range(self):
        """Test getting/setting the frame range.  If the frame
        range is not set on a layer, then it should default to
        the outline frame range.
        """
        outline.Outline.current = None
        ol = outline.Outline('after_init')
        layer = outline.layer.Frame('layer-name')
        ol.add_layer(layer)
        self.assertEqual(outline.layer.DEFAULT_FRAME_RANGE, layer.get_frame_range())


class LayerPreProcessTests(unittest.TestCase):

    def test_should_be_util_type_and_preprocess_service(self):
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        preprocess_layer = outline.layer.LayerPreProcess(parent_layer)

        self.assertEqual('Util', preprocess_layer.get_type())
        self.assertEqual('preprocess', preprocess_layer.get_service())

    def test_should_setup_depend_and_preprocess_layer(self):
        parent_layer_name = 'parent-layer'
        preprocess_layer_name = '%s_preprocess' % parent_layer_name
        parent_layer = outline.layer.Layer(parent_layer_name)
        preprocess_layer = outline.layer.LayerPreProcess(parent_layer)

        self.assertEqual(preprocess_layer_name, preprocess_layer.get_name())
        self.assertEqual(
            preprocess_layer_name, parent_layer.get_depends()[0].get_depend_on_layer().get_name())
        self.assertEqual(preprocess_layer, parent_layer.get_preprocess_layers()[0])

    def test_should_get_parent_layer(self):
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        preprocess_layer = outline.layer.LayerPreProcess(parent_layer)

        self.assertEqual(parent_layer, preprocess_layer.get_creator())

    def test_should_get_first_frame_of_layer_range(self):
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        parent_layer.set_frame_range('540-600')
        preprocess_layer = outline.layer.LayerPreProcess(parent_layer)

        self.assertEqual('540', preprocess_layer.get_frame_range())

    @mock.patch('outline.Layer.system', new=mock.Mock())
    def test_should_call_put_data_on_parent(self):
        os.environ = {}

        outline.Outline.current = None
        ol = outline.Outline('outline-name')
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        parent_layer.put_data = mock.Mock()
        ol.add_layer(parent_layer)

        preprocess_layer = outline.layer.LayerPreProcess(parent_layer)
        output = outline.io.Path('/path/to/output')
        preprocess_layer.add_output('output-name', output)
        ol.add_layer(preprocess_layer)

        with test_utils.TemporarySessionDirectory():
            ol.setup()
            preprocess_layer.execute(1)

            parent_layer.put_data.assert_called_with(
                'ol:outputs', {'output-name': output}, force=True)


class LayerPostProcessTests(unittest.TestCase):

    def test_should_be_util_type(self):
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        postprocess_layer = outline.layer.LayerPostProcess(parent_layer)

        self.assertEqual('Util', postprocess_layer.get_type())

    def test_should_setup_depend(self):
        parent_layer_name = 'parent-layer'
        postprocess_layer_name = '%s_postprocess' % parent_layer_name
        parent_layer = outline.layer.Layer(parent_layer_name)
        postprocess_layer = outline.layer.LayerPostProcess(parent_layer)

        self.assertEqual(postprocess_layer_name, postprocess_layer.get_name())
        self.assertEqual(
            parent_layer_name, postprocess_layer.get_depends()[0].get_depend_on_layer().get_name())

    def test_should_get_parent_layer(self):
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        postprocess_layer = outline.layer.LayerPostProcess(parent_layer)

        self.assertEqual(parent_layer, postprocess_layer.get_creator())


class OutlinePostCommandTests(unittest.TestCase):

    def test_should_be_post_type_and_postprocess_service(self):
        parent_layer_name = 'parent-layer'
        parent_layer = outline.layer.Layer(parent_layer_name)
        post_layer = outline.layer.OutlinePostCommand(parent_layer)

        self.assertEqual('Post', post_layer.get_type())
        self.assertEqual('postprocess', post_layer.get_service())


class TestAfterInit(outline.Layer):
    __test__ = False
    def __init__(self, name, **args):
        outline.Layer.__init__(self, name, **args)

    def after_init(self, ol):
        self.set_arg("after_init", True)


class TestA(outline.Layer):
    __test__ = False
    def __init__(self, name, **args):
        outline.Layer.__init__(self, name, **args)

    def setup(self):
        self.get_outline().add_layer(TestB("test_b"))


class TestB(outline.Layer):
    __test__ = False
    def __init__(self, name, **args):
        outline.Layer.__init__(self, name, **args)
        self.is_setup = False

    def setup(self):
        self.is_setup = True


if __name__ == '__main__':
    unittest.main()

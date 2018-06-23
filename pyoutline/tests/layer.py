#!/bin/env python2.5

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



import sys
import os
import unittest
import logging
import shutil

sys.path.insert(0,"../src")
import outline

logging.basicConfig(level=logging.INFO)

class CompositeTest(unittest.TestCase):
    """
    Tests for a composite layer. Composite layers
    can contain multiple layers.
    """

    def setUp(self):

        from outline.modules.shell import Shell

        self.ol = outline.Outline()
        self.layer = outline.Layer("composite")
        self.ol.add_layer(self.layer)

        self.layer.add_child(Shell("blah1", command=["ls","-l"]))
        self.layer.add_child(Shell("blah2", command=["ls","-1"]))
        self.layer.add_child(Shell("blah3", command=["ls"]))

        self.event = self.ol.get_layer("composite")

        self.ol.setup()

    def tearDown(self):
        """Remove the session directory that gets created if it exists."""
        try:
            shutil.rmtree(self.ol.get_session().get_path())
        except:
            pass

    def test_execute(self):
        """Run the execute method."""
        # Don't really have anything to assert here
        # besides the fact it actually runs.
        self.event.execute(1)

class ChunkingTest(unittest.TestCase):

    """Tests layer chunking."""

    def setUp(self):
        self.ol = outline.load_outline("scripts/shell.outline")
        self.ol.set_frame_range("1-10")

        self.event = self.ol.get_layer("cmd")
        self.event.set_chunk_size(5)
        self.ol.setup()

    def tearDown(self):
        """Remove the session directory that  gets created if it exists."""
        try:
            shutil.rmtree(self.ol.get_session().get_path())
        except:
            pass

    def test_get_locak_frame_set(self):
        """
        Test to make sure that that the localFrameSet is
        being constructed properly.  The local frame set
        is the frame list a particular frame is responsible
        for executing on the cue.  When the chunk-size is
        greated then 1, the local frame set will contain
        more than a single frame.
        """
        frames = self.event.get_local_frame_set(1);
        self.assertEquals(5, len(frames))
        for i in range(0,5):
            self.assertEquals(i+1,frames[i])

class RangeTests(unittest.TestCase):

    """Tests that the proper frame ranges are being resolved."""

    def setUp(self):
        self.__ol = []

    def tearDown(self):
        """Remove the session directory that  gets created if it exists."""
        for ol in self.__ol:
            try:
                shutil.rmtree(self.ol.get_session().get_path())
            except:
                pass

    def test_no_layer_range_no_job_range(self):
        ol = outline.load_outline("scripts/shell.outline")
        self.__ol.append(ol)

        # No layer range, no outline range defaults to a single frame.
        self.assertEquals("1000-1000", ol.get_layer("cmd").get_frame_range())
        self.assertEquals(None, ol.get_frame_range())

    def test_no_layer_range_job_range(self):
        ol = outline.load_outline("scripts/shell.outline")
        self.__ol.append(ol)
        ol.set_frame_range("1000-2000")

        # No layer range, no outline range defaults to a single frame.
        self.assertEquals("1000-2000", ol.get_layer("cmd").get_frame_range())
        self.assertEquals("1000-2000", ol.get_frame_range())

    def test_layer_range_no_job_range(self):
        ol = outline.load_outline("scripts/shell.outline")
        self.__ol.append(ol)

        ol.get_layer("cmd").set_frame_range("1000-2000")
        self.assertEquals("1000-2000", ol.get_layer("cmd").get_frame_range())
        self.assertEquals(None, ol.get_frame_range())

    def test_layer_range_job_range(self):
        ol = outline.load_outline("scripts/shell.outline")
        self.__ol.append(ol)

        ol.set_frame_range("1000-2000")
        ol.get_layer("cmd").set_frame_range("1000-2000")

        self.assertEquals("1000-2000", ol.get_layer("cmd").get_frame_range())
        self.assertEquals("1000-2000", ol.get_frame_range())

    def test_intersecting_range(self):
        ol = outline.load_outline("scripts/shell.outline")
        self.__ol.append(ol)

        ol.set_frame_range("1000-2000x8")
        ol.get_layer("cmd").set_frame_range("1000-2000")

        self.assertEquals("1000-2000x8", ol.get_layer("cmd").get_frame_range())
        self.assertEquals("1000-2000x8", ol.get_frame_range())

    def test_intersecting_failure(self):
        ol = outline.load_outline("scripts/shell.outline")
        self.__ol.append(ol)

        ol.set_frame_range("1000-1010")
        ol.get_layer("cmd").set_frame_range("1100-1200")

        self.assertFalse(ol.get_layer("cmd").get_frame_range())

class LayerTest(unittest.TestCase):
    """Tests for outline layer."""

    def setUp(self):
        """Setup a basis event from a preset outline file."""
        path = "scripts/shell.outline"
        self.ol = outline.load_outline(path)
        self.ol.set_frame_range("1-10")
        self.event = self.ol.get_layer("cmd")

    def tearDown(self):
        """Remove the session directory that  gets created if it exists."""
        try:
            shutil.rmtree(self.ol.get_session().get_path())
        except:
            pass

    def test_name(self):
        """Test the name has been set properly."""
        self.assertEqual("cmd", self.event.get_name())

    def test_to_string(self):
        """Tests to ensure __str__ returns the layer name."""
        self.assertEqual(self.event.get_name(), str(self.event))

    def test_get_set_args(self):
        """Test the arguement getter/setter methods."""

        self.assertEqual(self.event.get_arg("test1"), 1)
        self.assertEqual(self.event.get_arg("test2"), 2)

        self.event.set_arg("foo",1)
        self.assertEqual(1, self.event.get_arg("foo"))
        self.assertEqual(1, self.event.get_arg("bar",1))

    def test_invalid_type_args(self):
        """Test the interpolation of arg strings."""

        self.event.require_arg("shazam", (str))
        self.assertRaises(outline.layer.LayerException, self.event.set_arg, "shazam", { })

        self.event.set_arg("shazam", "shazoo")

    def test_require_arg(self):
        """
        Test required arguments.  Unset required args will
        throw a LayerException if they are not set before
        setup() is run.
        """
        self.event.require_arg("bobofet")
        self.assertRaises(outline.layer.LayerException, self.event.check_required_args)
        self.event.set_arg("bobofet",1)
        self.event.check_required_args()

    def test_get_path(self):
        """Test that the layer session path is correct."""
        self.assertRaises(outline.OutlineException, self.event.get_path)
        self.ol.setup()
        self.assertEquals("%s/layers/%s" % (self.ol.get_session().get_path(),
                          self.event.get_name()), self.event.get_path())

    def test_setup(self):
        """Test setting up the event for launch."""
        self.event.setup()

    def test_execute(self):
        """Test execution of a frame."""
        self.ol.setup()
        self.event.execute(1)

    def test_get_set_frame_range(self):
        """Test getting/setting the frame range.  If the frame
        range is not set on a layer, then it should default to
        the outline frame range.
        """
        self.assertEquals(self.ol.get_frame_range(), self.event.get_frame_range())
        self.event.set_frame_range("1-10")
        self.assertEquals("1-10", self.event.get_frame_range())

    def test_get_set_chunk_size(self):
        """Test get/set of chunk size."""
        self.event.set_chunk_size(5)
        self.assertEquals(5, self.event.get_chunk_size())

    def test_add_layer_during_setup(self):
        """Test to ensure that layers added during setup are serialized."""

        ol = outline.Outline("mr_hat")
        ol.add_layer(TestA("test_a"))
        ol.setup()

        ol_b = outline.load_outline(ol.get_session().get_file("outline.yaml"))
        # ensure the new layer was added
        self.assertTrue(ol_b.get_layer("test_b"))
        #  ensure that setup was actually run on the new layer
        self.assertTrue(ol_b.get_layer("test_b").is_setup)

    def test_after_init(self):
        ol = outline.Outline("after_init")
        ol.add_layer(TestAfterInit("test"))

        # Ensure after init was run,
        self.assertTrue(ol.get_layer("test").get_arg("after_init"))
        # Ensure that the layer has the right ol reference
        self.assertEquals(ol, ol.get_layer("test").get_outline())

    def test_after_init_current(self):
        ol = outline.Outline("after_init", current=True)
        TestAfterInit("test")

        # Ensure after init was run,
        self.assertTrue(ol.get_layer("test").get_arg("after_init"))
        # Ensure that the layer has the right ol reference
        self.assertEquals(ol, ol.get_layer("test").get_outline())

    def test_dependency_creation(self):

        outline.Outline.current = None
        ol = outline.Outline("after_init")
        ol.add_layer(TestAfterInit("test"))
        ol.add_layer(TestB("testb", require="test"))
        ol.setup()

        # check the depend was setup properly
        self.assertEquals(1, len(ol.get_layer("testb").get_depends()))

    def test_type_arg(self):
        """Test to ensure the type argument is handled properly."""
        outline.Outline.current = None
        t = TestA("test", type="Post")
        self.assertEquals("Post", t.get_type())

    def test_set_output_attribute(self):
        """Test setting an output attribute on all registered output."""
        t = TestA("test")
        t.add_output("node1", outline.io.Path("/tmp"))
        t.set_output_attribute("test", True)
        self.assertTrue(t.get_output("node1").get_attribute("test"))

    def test_set_output_attribute(self):
        """Test setting an input attribute on all registered input."""
        t = TestA("test")
        t.add_input("node1", outline.io.Path("/tmp"))
        t.set_input_attribute("test", True)
        self.assertTrue(t.get_input("node1").get_attribute("test"))

class OutputRegistrationTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None

    def test_output_passing(self):
        """
        Test that output registered in a pre-process is serialized
        to a ol:outputs file in the render layer.
        """
        ol = outline.Outline("pre_test")

        # the render layer
        layer1 = TestA("test1")

        # the preprocess
        prelayer = outline.layer.LayerPreProcess(layer1)
        prelayer._execute = lambda frames: prelayer.add_output("test",
                                                               outline.io.FileSpec("/tmp/foo.#.exr"))
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
        self.assertEquals(1, len(layer1.get_outputs()))


class TestAfterInit(outline.Layer):
    def __init__(self, name, **args):
        outline.Layer.__init__(self, name, **args)
    def after_init(self, ol):
        self.set_arg("after_init", True)

class TestA(outline.Layer):
    def __init__(self, name, **args):
        outline.Layer.__init__(self, name, **args)
    def setup(self):
        self.get_outline().add_layer(TestB("test_b"))

class TestB(outline.Layer):
    def __init__(self, name, **args):
        outline.Layer.__init__(self, name, **args)
    def setup(self):
        self.is_setup = True

if __name__ == '__main__':
    unittest.main()


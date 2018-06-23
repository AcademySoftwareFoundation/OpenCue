#!/usr/local64/bin/python2.5

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


import os
import sys
import unittest

from xml.etree import ElementTree as Et

sys.path.insert(0,"../../src")
import outline

class Cue3BackendTest(unittest.TestCase):
    """
    Tests to ensure that the Cue3 spec generator
    is doing its job.
    """
    script = os.path.dirname(__file__) + "../scripts/shell.outline"
    
    def test_ol_tag_override_env(self):
        """
        Check that the OL_TAG_OVERRIDE environment variable
        is handled properly.
        """
        ol = outline.load_outline(Cue3BackendTest.script)
        for layer in ol.get_layers():
            layer.set_arg("tags", ["foo", "man", "chu"])
        
        try:
            os.environ["OL_TAG_OVERRIDE"] = "general"
            l = outline.cuerun.OutlineLauncher(ol)
    
            root = Et.fromstring(l.serialize())
            self.assertEquals(os.environ["OL_TAG_OVERRIDE"], 
                              root.find("job/layers/layer/tags").text)
        finally:
            del os.environ["OL_TAG_OVERRIDE"]
        
        
    def test_tags_as_list(self):
        """Check that tags passed in as a list."""
        
        ol = outline.load_outline(Cue3BackendTest.script)
        for layer in ol.get_layers():
            layer.set_arg("tags", ["foo", "man", "chu"])
            
        l = outline.cuerun.OutlineLauncher(ol)
        root = Et.fromstring(l.serialize())
        self.assertEquals("foo | man | chu", 
                          root.find("job/layers/layer/tags").text)
        
    def test_tags_as_string(self):
        """Check tags passed in as a string."""
        
        ol = outline.load_outline(Cue3BackendTest.script)
        for layer in ol.get_layers():
            layer.set_arg("tags", "foo | man | chu")
            
        l = outline.cuerun.OutlineLauncher(ol)
        root = Et.fromstring(l.serialize())
        self.assertEquals("foo | man | chu", 
                          root.find("job/layers/layer/tags").text)
        
    def test_os_flag(self):
        """
        Check that the os flag is handled properly.
        """
        ol = outline.load_outline(Cue3BackendTest.script)
        l = outline.cuerun.OutlineLauncher(ol, os="awesome")
        
        root = Et.fromstring(l.serialize())
        self.assertEquals("awesome", 
                          root.find("job/os").text)
        
    def test_ol_os_env(self):
        """
        Check that the OL_OS environment variable
        is handled properly.
        """
        try:
            os.environ["OL_OS"] = "radical"
            ol = outline.load_outline(Cue3BackendTest.script)
            l = outline.cuerun.OutlineLauncher(ol)
            root = Et.fromstring(l.serialize())
            self.assertEquals("radical", 
                              root.find("job/os").text)
        finally:
            del os.environ["OL_OS"]

if __name__ == '__main__':
    unittest.main()


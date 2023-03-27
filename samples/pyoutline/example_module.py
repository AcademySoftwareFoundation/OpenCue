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


from outline import Layer


def ExampleModule(Layer):

    """
    An example outline module that implements all possible
    abtract functions.
    """

    def __init__(self, name, **args):
        Layer.__init__(self, name, **args)

    def after_init(self):
        """
        Executed automatically after the constructor.  This method
        exists because the parent outline is not known in the constructor.
        """
        outline = self.get_outline()

    def after_parented(self):
        """
        Executed automatically after the layer has been parented
        to another layer.  This only happens when building
        composite layers, or, layers that contain other layers.
        """
        parent_layer = self.get_parent()

    def _setup(self):
        """
        Should contain any operations that should be run before the job
        is launched.  This is the first time the session becomes
        available, so its possible to write data into the cue_archive.
        """
        pass

    def _before_execute(self):
        """
        Run before execute.  Generally used to create objects that do
        not serialize to pickle properly for job launch.
        """

    def _execute(self, frames):
        """
        The core module behavior should be implemented here.  The
        frames argument contains an array of frames that the current
        instance is responsible for.
        """
        pass

    def _after_execute(self):
        """
        Run after execute even if execute throws an exception.  Used for
        cleanup and implementing extra output checks like checking for
        black frames or log parsing.
        """
        pass









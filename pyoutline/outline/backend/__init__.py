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
PyOutline output modules.

PyOutline can be thought of as separate from OpenCue proper -- it is just a job specification
after all, and could be used in any number of contexts.

To this end, PyOutline supports launching jobs on any number of "backends", i.e. the system
responsible for processing the job -- launching the job / frames, storing job state, etc.

The main backend of course is OpenCue (`outline.backend.cue`), which launches the job on OpenCue.
However this can be extended to support any job management system. We also include a "local"
backend (`outline.backend.local`) which just runs the job on the current machine, using a SQLite
database for storing state.
"""

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


"""OpenCue Cuecmd command execution tool."""

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("opencue_cuecmd")
    except PackageNotFoundError:
        # Package is not installed
        __version__ = "1.0.0"
except ImportError:
    # Python < 3.8
    try:
        import pkg_resources

        __version__ = pkg_resources.get_distribution("opencue_cuecmd").version
    except Exception:
        __version__ = "1.0.0"

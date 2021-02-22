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


"""Custom exception classes used throughout RQD."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import


class RqdException(Exception):
    """Generic exception from the RQD code."""


class CoreReservationFailureException(Exception):
    """RQD failed to reserve the required number of cores."""


class DuplicateFrameViolationException(Exception):
    """RQD attempted to book a frame that was already running."""


class InvalidUserException(Exception):
    """RQD attempted to assume the role of an invalid user."""

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


"""Pytests for rqd.rqcore"""


import sys
import types


def _install_minimal_stubs(monkeypatch):
    """Install tiny stubs for psutil and rqd.rqmachine."""
    # psutil stub
    psutil = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, 'psutil', psutil)
    # rqd.rqmachine stub
    rqmachine = types.SimpleNamespace(Machine=type('M', (), {}))
    monkeypatch.setitem(sys.modules, 'rqd.rqmachine', rqmachine)


def _bare_attendant_with_log(path, rqcore):
    """Create a minimal FrameAttendantThread with only ``log_dir_file`` set."""
    att = object.__new__(rqcore.FrameAttendantThread)
    att.runFrame = types.SimpleNamespace(log_dir_file=str(path))
    return att


def test_log_size_limit_under_threshold(tmp_path, monkeypatch):
    """Returns (False, "") when file size is below the configured threshold."""
    _install_minimal_stubs(monkeypatch)
    from rqd import rqcore, rqconstants  # pylint: disable=import-outside-toplevel

    log_file = tmp_path / 'job.frame.rqlog'
    log_file.write_text('hello\n', encoding='utf-8')

    monkeypatch.setattr(rqconstants, 'JOB_LOG_MAX_SIZE_IN_BYTES', 1024)
    att = _bare_attendant_with_log(log_file, rqcore)
    exceeded, msg = att._FrameAttendantThread__log_size_limit_exceeded()

    assert exceeded is False
    assert msg == ''


def test_log_size_limit_exceeded(tmp_path, monkeypatch):
    """Returns (True, message) when file size exceeds the threshold.

    The message should include the log path and mention termination.
    """
    _install_minimal_stubs(monkeypatch)
    from rqd import rqcore, rqconstants  # pylint: disable=import-outside-toplevel

    log_file = tmp_path / 'job.frame.rqlog'
    log_file.write_bytes(b'x' * 2048)

    monkeypatch.setattr(rqconstants, 'JOB_LOG_MAX_SIZE_IN_BYTES', 1024)
    att = _bare_attendant_with_log(log_file, rqcore)
    exceeded, msg = att._FrameAttendantThread__log_size_limit_exceeded()

    assert exceeded is True
    assert str(log_file) in msg
    assert 'Terminating job' in msg

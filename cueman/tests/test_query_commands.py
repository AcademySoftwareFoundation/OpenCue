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


"""Unit tests for cueman query and listing commands (-lf, -lp, -ll, -info)."""

import unittest
from unittest import mock
import argparse

from cueman import main as cueman_main


def build_args(**kwargs):
    # Set all possible attributes to None unless specified
    fields = [
        "lf", "lp", "ll", "info",
        "pause", "resume", "term", "eat", "kill", "retry", "done",
        "stagger", "reorder", "retries", "autoeaton", "autoeatoff",
        "force",
        # frame/proc filter options
        "layer", "state", "range", "memory", "duration", "page", "limit",
        # general options cueman accepts
        "server", "facility", "verbose",
    ]
    args_dict = {f: kwargs.get(f, None) for f in fields}
    # Defaults
    if "force" not in kwargs:
        args_dict["force"] = False
    return argparse.Namespace(**args_dict)


class TestCuemanQueryCommands(unittest.TestCase):
    @mock.patch("opencue.api.findJob")
    @mock.patch("cueadmin.output.displayFrames")
    @mock.patch("cueman.main.buildFrameSearch")
    def test_list_frames_with_layer_and_state_filters(
        self, mock_buildFrameSearch, mock_display, mock_findJob
    ):
        args = build_args(lf="job1", layer=["layerA"], state=["RUNNING"], limit=1000)
        job = mock.Mock()
        job.getFrames.return_value = ["frame1", "frame2"]
        mock_findJob.return_value = job
        mock_buildFrameSearch.return_value = {
            "layer": ["layerA"],
            "state": ["RUNNING"],
            "limit": 1000,
        }

        cueman_main.handleArgs(args)

        mock_buildFrameSearch.assert_called_once_with(args)
        job.getFrames.assert_called_once_with(
            layer=["layerA"], state=["RUNNING"], limit=1000
        )
        mock_display.assert_called_once_with(["frame1", "frame2"])

    @mock.patch("opencue.api.getProcs")
    @mock.patch("cueadmin.output.displayProcs")
    def test_list_processes_with_memory_and_duration_filters(self, mock_display, mock_getProcs):
        # cueman_main._get_proc_filters will compute duration_range.
        args = build_args(lp="job1", memory="2-4", duration="1-2", limit=1000)
        mock_getProcs.return_value = ["proc1", "proc2"]

        cueman_main.handleArgs(args)

        mock_display.assert_called_once_with(["proc1", "proc2"])

    @mock.patch("opencue.api.findJob")
    @mock.patch("cueadmin.output.displayJobInfo")
    def test_job_info_display(self, mock_display, mock_findJob):
        args = build_args(info="job1")
        job = mock.Mock()
        mock_findJob.return_value = job

        cueman_main.handleArgs(args)

        mock_display.assert_called_once_with(job)

    @mock.patch("opencue.api.findJob")
    @mock.patch("cueadmin.output.displayFrames")
    @mock.patch("cueman.main.buildFrameSearch")
    def test_pagination_and_limit(
        self, mock_buildFrameSearch, mock_display, mock_findJob
    ):
        args = build_args(lf="job1", page=2, limit=500)
        job = mock.Mock()
        job.getFrames.return_value = ["frameA", "frameB"]
        mock_findJob.return_value = job
        mock_buildFrameSearch.return_value = {"page": 2, "limit": 500}

        cueman_main.handleArgs(args)

        mock_buildFrameSearch.assert_called_once_with(args)
        job.getFrames.assert_called_once_with(page=2, limit=500)
        mock_display.assert_called_once_with(["frameA", "frameB"])

    @mock.patch("opencue.api.findJob")
    @mock.patch("cueadmin.output.displayFrames")
    @mock.patch("cueman.main.buildFrameSearch")
    def test_empty_result_handling(
        self, mock_buildFrameSearch, mock_display, mock_findJob
    ):
        args = build_args(lf="job1", limit=1000)
        job = mock.Mock()
        job.getFrames.return_value = []
        mock_findJob.return_value = job
        mock_buildFrameSearch.return_value = {"limit": 1000}

        cueman_main.handleArgs(args)

        job.getFrames.assert_called_once_with(limit=1000)
        mock_display.assert_called_once_with([])

    @mock.patch("opencue.api.findJob")
    @mock.patch("cueadmin.output.displayFrames")
    @mock.patch("cueman.main.buildFrameSearch")
    def test_large_dataset_performance(
        self, mock_buildFrameSearch, mock_display, mock_findJob
    ):
        args = build_args(lf="job1", limit=1000)
        job = mock.Mock()
        job.getFrames.return_value = [f"frame{i}" for i in range(2000)]
        mock_findJob.return_value = job
        mock_buildFrameSearch.return_value = {"limit": 1000}

        cueman_main.handleArgs(args)

        job.getFrames.assert_called_once_with(limit=1000)
        mock_display.assert_called_once_with([f"frame{i}" for i in range(2000)])

    @mock.patch("opencue.api.findJob")
    @mock.patch("cueadmin.output.displayFrames")
    @mock.patch("cueman.main.buildFrameSearch")
    def test_filter_combination(
        self, mock_buildFrameSearch, mock_display, mock_findJob
    ):
        args = build_args(
            lf="job1",
            layer=["layerA", "layerB"],
            state=["RUNNING", "WAITING"],
            range="1-100",
            memory="gt2",
            duration="lt1",
            page=1,
            limit=50,
        )
        job = mock.Mock()
        job.getFrames.return_value = ["frameX", "frameY"]
        mock_findJob.return_value = job
        mock_buildFrameSearch.return_value = {
            "layer": ["layerA", "layerB"],
            "state": ["RUNNING", "WAITING"],
            "range": "1-100",
            "page": 1,
            "limit": 50,
        }

        cueman_main.handleArgs(args)

        mock_buildFrameSearch.assert_called_once_with(args)
        job.getFrames.assert_called_once()
        mock_display.assert_called_once_with(["frameX", "frameY"])

    @mock.patch("opencue.api.findJob")
    @mock.patch("cueman.main.displayLayers")
    def test_list_layers_with_formatting_and_statistics(self, mock_displayLayers, mock_findJob):
        args = build_args(ll="job1")
        job = mock.Mock()
        mock_findJob.return_value = job

        cueman_main.handleArgs(args)

        mock_displayLayers.assert_called_once_with(job)

if __name__ == "__main__":
    unittest.main()

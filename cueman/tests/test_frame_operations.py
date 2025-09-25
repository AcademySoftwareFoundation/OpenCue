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
Unit tests for frame operations cueman
"""

import unittest
from unittest.mock import MagicMock, patch
import argparse
from cueman import main as cuemain

class TestFrameOperations (unittest.TestCase):
    """
    Test cases for cueman frame operations
    """

    def _ns(self, **overrides):
        """Build a minimal argparse.Namespace matching cueman.main expectations."""
        base = {
            "lf": None,
            "lp": None,
            "ll": None,
            "info": None,
            "pause": None,
            "resume": None,
            "term": None,
            "eat": None,
            "kill": None,
            "retry": None,
            "done": None,
            "stagger": None,
            "reorder": None,
            "retries": None,
            "autoeaton": None,
            "autoeatoff": None,
            "layer": None,
            "range": None,
            "state": None,
            "page": None,
            "limit": None,
            "duration": None,
            "memory": None,
            "force": False,
        }
        base.update(overrides)
        return argparse.Namespace(**base)
        

    @patch("opencue.api.findJob")
    def test_eatFrames_with_valid_layer(self, mock_findJob):
        """Test eatFrames with valid layer and range filters."""
        mock_job = MagicMock()
        mock_frame = MagicMock()
        mock_job.getFrames.return_value = [mock_frame]
        mock_job.eatFrames = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(eat="test_job", layer="render_layer", range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.eatFrames.assert_called_once_with(layer="render_layer" , range="1-10")
        

    @patch("opencue.api.findJob")
    def test_killFrames_with_valid_layer(self, mock_findJob):
        """Test killFrames with valid layer and range filters."""
        mock_job = MagicMock()
        mock_frame = MagicMock()
        mock_job.getFrames.return_value = [mock_frame]
        mock_job.killFrames = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(kill="test_job", layer="render_layer", range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.killFrames.assert_called_once_with(layer="render_layer", range="1-10")


    @patch("opencue.api.findJob")
    def test_retryFrames_with_valid_layer(self, mock_findJob):
        """Test retryFrames with valid layer and range filters."""
        mock_job = MagicMock()
        mock_frame = MagicMock()
        mock_job.getFrames.return_value = [mock_frame]
        mock_job.retryFrames = MagicMock()
        mock_findJob.return_value = mock_job

        args = self._ns(retry="test_job", layer="render_layer", range="1-10", force=True)
        cuemain.handleArgs(args)

        mock_findJob.assert_called_once_with("test_job")
        mock_job.retryFrames.assert_called_once_with(layer="render_layer", range="1-10")
    

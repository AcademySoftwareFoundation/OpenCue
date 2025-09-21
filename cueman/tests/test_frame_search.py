"""
Unit tests for buildFrameSearch function in cueman.main
"""

import unittest
from unittest import mock

try:
    from opencue.compiled_proto import job_pb2
except ImportError:
    try:
        from opencue_proto import job_pb2
    except ImportError:
        class JobPb2Mock:
            RUNNING = 'RUNNING'
            WAITING = 'WAITING'
        job_pb2 = JobPb2Mock()

import cueman.main as main

class TestBuildFrameSearch(unittest.TestCase):
	def setUp(self):
		self.default_args = mock.Mock()
		self.default_args.layer = None
		self.default_args.range = None
		self.default_args.state = None
		self.default_args.memory = 0.01
		self.default_args.duration = 0.01
		self.default_args.page = None
		self.default_args.limit = 1000

	def test_default_search(self):
		with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
			mock_handle.side_effect = [
				[mock.Mock(value=10485)],  # memory conversion
				[mock.Mock(value=36)],     # duration conversion
			]
			result = main.buildFrameSearch(self.default_args)
		expected = {"memory": "0-10485", "duration": "0-36", "limit": 1000}
		self.assertEqual(result, expected)

	def test_layer_filter(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.layer = ["layer1", "layer2"]
		result = main.buildFrameSearch(args)
		self.assertIn("layer", result)
		self.assertEqual(result["layer"], ["layer1", "layer2"])

	def test_range_filter(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.range = "1-100"
		result = main.buildFrameSearch(args)
		self.assertIn("range", result)
		self.assertEqual(result["range"], "1-100")

	def test_state_filter_conversion(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.state = ["RUNNING", "WAITING"]
		with mock.patch("cueadmin.common.Convert.strToFrameState") as mock_convert:
			mock_convert.side_effect = [job_pb2.RUNNING, job_pb2.WAITING]
			result = main.buildFrameSearch(args)
		self.assertIn("state", result)
		self.assertEqual(result["state"], [job_pb2.RUNNING, job_pb2.WAITING])

	def test_memory_filter(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.memory = "2-4"
		with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
			mock_handle.return_value = [mock.Mock(value=2097152), mock.Mock(value=4194304)]
			result = main.buildFrameSearch(args)
		self.assertIn("memory", result)

	def test_duration_filter(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.duration = "1-2"
		with mock.patch("cueadmin.common.handleIntCriterion") as mock_handle:
			mock_handle.return_value = [mock.Mock(value=3600), mock.Mock(value=7200)]
			result = main.buildFrameSearch(args)
		self.assertIn("duration", result)

	def test_pagination_inclusion(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.page = 2
		result = main.buildFrameSearch(args)
		self.assertIn("page", result)
		self.assertEqual(result["page"], 2)

	def test_limit_inclusion(self):
		args = mock.Mock(**self.default_args.__dict__)
		args.limit = 500
		result = main.buildFrameSearch(args)
		self.assertIn("limit", result)
		self.assertEqual(result["limit"], 500)

	def test_empty_filters(self):
		args = mock.Mock()
		args.layer = None
		args.range = None
		args.state = None
		args.memory = None
		args.duration = None
		args.page = None
		args.limit = None
		result = main.buildFrameSearch(args)
		self.assertEqual(result, {})

if __name__ == "__main__":
	unittest.main()

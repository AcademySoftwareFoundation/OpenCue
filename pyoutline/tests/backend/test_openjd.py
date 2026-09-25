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

"""Tests for the OpenJD backend module."""

import os
import tempfile
import textwrap
import unittest
from unittest import mock

import yaml

import outline
import outline.backend.openjd
import outline.cuerun
import outline.exception
import outline.modules.shell

TEST_USER = "test-user"

# The wrapper script preamble is the same for every step.
WRAPPER_PREAMBLE = """\
#!/bin/bash
export CUE_IFRAME={{ min(Task.Param.Frame) }}
export CUE_JOB={{ repr_sh(Job.Name) }}
export CUE_LAYER={{ repr_sh(Step.Name) }}
export CUE_FRAME={{ repr_sh(zfill(min(Task.Param.Frame), 4) + '-' + Step.Name) }}
"""


def _serialize(ol):
    """Helper: serialize an Outline and return the parsed template dict."""
    launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
    return yaml.safe_load(outline.backend.openjd.serialize(launcher))


def _wrapper_data(step):
    """Extract the wrapper script content from a step dict."""
    for ef in step["script"]["embeddedFiles"]:
        if ef["name"] == "opencue_wrapper":
            return ef["data"]
    raise KeyError("No wrapper embedded file found")


def _expected(yaml_str):
    """Helper: parse a YAML string into a dict for comparison."""
    return yaml.safe_load(textwrap.dedent(yaml_str))


class SerializeBasicTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_single_layer(self):
        ol = outline.Outline("test-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell("render", command=["echo", "#IFRAME#"], range="1-10")
        )

        self.assertEqual(
            _serialize(ol),
            _expected("""
                name: test-job
                specificationVersion: jobtemplate-2023-09
                extensions: [TASK_CHUNKING, EXPR]
                parameterDefinitions:
                  - name: Facility
                    type: STRING
                    default: 'local'
                  - name: Show
                    type: STRING
                    default: testing
                  - name: Shot
                    type: STRING
                    default: test
                  - name: User
                    type: STRING
                    default: test-user
                jobEnvironments:
                  - name: cue-env
                    variables:
                      CUE3: '1'
                      CUE_SHOW: '{{ Param.Show }}'
                      CUE_SHOT: '{{ Param.Shot }}'
                      CUE_USER: '{{ Param.User }}'
                steps:
                  - name: render
                    let:
                      - frames = range_expr("1-10")
                      - chunk_size = 1
                    stepEnvironments:
                      - name: render-env
                        variables:
                          CUE_RANGE: '{{ frames }}'
                          CUE_CHUNK: '{{ chunk_size }}'
                          CUE_THREADABLE: '0'
                    parameterSpace:
                      taskParameterDefinitions:
                        - name: Frame
                          type: 'CHUNK[INT]'
                          range: '{{ frames }}'
                          chunks:
                            defaultTaskCount: '{{ chunk_size }}'
                            rangeConstraint: CONTIGUOUS
                    script:
                      actions:
                        onRun:
                          command: '{{ Task.File.opencue_wrapper }}'
                      embeddedFiles:
                        - name: opencue_wrapper
                          type: TEXT
                          runnable: true
                          data: |
                            #!/bin/bash
                            export CUE_IFRAME={{ min(Task.Param.Frame) }}
                            export CUE_JOB={{ repr_sh(Job.Name) }}
                            export CUE_LAYER={{ repr_sh(Step.Name) }}
                            export CUE_FRAME={{ repr_sh(zfill(min(Task.Param.Frame), 4) + '-' + Step.Name) }}
                            exec echo '{{ min(Task.Param.Frame) }}'
                    hostRequirements:
                      attributes:
                        - name: 'opencue:attr.service'
                          anyOf: [shell]
            """),
        )


class SerializeDependenciesTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_layer_dependency(self):
        ol = outline.Outline("dep-job", shot="test", show="testing", user=TEST_USER)
        l1 = outline.modules.shell.Shell("render", command=["render", "#IFRAME#"], range="1-100")
        ol.add_layer(l1)
        l2 = outline.modules.shell.Shell(
            "composite", command=["comp", "#IFRAME#"], range="1-100", chunk=100
        )
        l2.depend_all(l1)
        ol.add_layer(l2)

        template = _serialize(ol)
        self.assertEqual(2, len(template["steps"]))
        self.assertNotIn("dependencies", template["steps"][0])
        self.assertEqual([{"dependsOn": "render"}], template["steps"][1]["dependencies"])
        # Composite step has chunk=100
        self.assertEqual(
            "{{ chunk_size }}",
            template["steps"][1]["parameterSpace"]["taskParameterDefinitions"][0]["chunks"][
                "defaultTaskCount"
            ],
        )


class SerializeHostRequirementsTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_cores_and_memory(self):
        ol = outline.Outline("resource-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell(
                "heavy", command=["render"], range="1-10", cores=8, memory="4g"
            )
        )

        template = _serialize(ol)
        self.assertEqual(
            template["steps"][0]["hostRequirements"],
            _expected("""
                amounts:
                  - name: amount.worker.vcpu
                    min: 8.0
                  - name: amount.worker.memory
                    min: 4096
                attributes:
                  - name: 'opencue:attr.service'
                    anyOf: [shell]
            """),
        )


class SerializeEnvironmentTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_layer_env(self):
        ol = outline.Outline("env-job", shot="test", show="testing", user=TEST_USER)
        layer = outline.modules.shell.Shell("render", command=["render"], range="1-5")
        layer.set_env("RENDERER", "prman")
        layer.set_env("THREADS", "8")
        ol.add_layer(layer)

        template = _serialize(ol)
        env_vars = template["steps"][0]["stepEnvironments"][0]["variables"]
        # User env vars are included alongside per-step CUE_* vars
        self.assertEqual("prman", env_vars["RENDERER"])
        self.assertEqual("8", env_vars["THREADS"])
        self.assertEqual("{{ frames }}", env_vars["CUE_RANGE"])
        # Job-wide CUE_* vars are in jobEnvironments
        job_env_vars = template["jobEnvironments"][0]["variables"]
        self.assertEqual("1", job_env_vars["CUE3"])


class FrameRangeConversionTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_step_syntax(self):
        self.assertEqual("1-100:2", outline.backend.openjd._frame_range_to_openjd("1-100x2"))

    def test_simple_range(self):
        self.assertEqual("1-50", outline.backend.openjd._frame_range_to_openjd("1-50"))


class MemoryParsingTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_megabytes_suffix(self):
        self.assertEqual(512, outline.backend.openjd._parse_memory_to_mib("512m"))

    def test_gigabytes_suffix(self):
        self.assertEqual(4096, outline.backend.openjd._parse_memory_to_mib("4g"))

    def test_plain_number_treated_as_gb(self):
        self.assertEqual(8192, outline.backend.openjd._parse_memory_to_mib("8"))

    def test_fractional_gigabytes(self):
        self.assertEqual(1536, outline.backend.openjd._parse_memory_to_mib("1.5g"))

    def test_uppercase_suffix(self):
        self.assertEqual(512, outline.backend.openjd._parse_memory_to_mib("512M"))

    def test_invalid_raises(self):
        with self.assertRaises(outline.exception.LayerException):
            outline.backend.openjd._parse_memory_to_mib("bogus")


class LaunchTest(unittest.TestCase):
    @mock.patch("outline.backend.openjd.subprocess.run")
    def test_launch_calls_openjd_run(self, mock_run):
        mock_run.return_value = mock.Mock(returncode=0)

        ol = outline.Outline("launch-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(outline.modules.shell.Shell("cmd", command=["echo", "hello"], range="1-1"))

        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        result = outline.backend.openjd.launch(launcher)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(["openjd", "run"], cmd[:2])
        self.assertTrue(cmd[2].endswith(".template.yaml"))

        template = yaml.safe_load(result)
        self.assertEqual("jobtemplate-2023-09", template["specificationVersion"])

    @mock.patch("outline.backend.openjd.subprocess.run")
    def test_launch_raises_on_failure(self, mock_run):
        mock_run.return_value = mock.Mock(returncode=1, stderr="error output")

        ol = outline.Outline("fail-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(outline.modules.shell.Shell("cmd", command=["false"], range="1-1"))

        launcher = outline.cuerun.OutlineLauncher(ol, user=TEST_USER)
        with self.assertRaises(outline.exception.OutlineException):
            outline.backend.openjd.launch(launcher)


class SerializeTimeoutTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_timeout_mapped(self):
        ol = outline.Outline("timeout-job", shot="test", show="testing", user=TEST_USER)
        layer = outline.modules.shell.Shell("render", command=["render"], range="1-10")
        layer.set_arg("timeout", 3600)
        ol.add_layer(layer)

        template = _serialize(ol)
        action = template["steps"][0]["script"]["actions"]["onRun"]
        self.assertEqual(3600, action["timeout"])

    def test_no_timeout_omitted(self):
        ol = outline.Outline("no-timeout-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(outline.modules.shell.Shell("render", command=["render"], range="1-10"))

        template = _serialize(ol)
        action = template["steps"][0]["script"]["actions"]["onRun"]
        self.assertNotIn("timeout", action)


class SerializeTagsAndServiceTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_tags_as_string(self):
        ol = outline.Outline("tag-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell(
                "render", command=["render"], range="1-10", tags="render|gpu"
            )
        )

        self.assertEqual(
            _serialize(ol)["steps"][0]["hostRequirements"],
            _expected("""
                attributes:
                  - name: 'opencue:attr.tag'
                    allOf: [render, gpu]
                  - name: 'opencue:attr.service'
                    anyOf: [shell]
            """),
        )

    def test_service_attribute(self):
        ol = outline.Outline("svc-job", shot="test", show="testing", user=TEST_USER)
        layer = outline.modules.shell.Shell("render", command=["render"], range="1-10")
        layer.set_service("prman")
        ol.add_layer(layer)

        self.assertEqual(
            _serialize(ol)["steps"][0]["hostRequirements"],
            _expected("""
                attributes:
                  - name: 'opencue:attr.service'
                    anyOf: [prman]
            """),
        )

    def test_tags_and_cores_combined(self):
        ol = outline.Outline("combo-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell(
                "render", command=["render"], range="1-10", tags="render|gpu", cores=16
            )
        )

        self.assertEqual(
            _serialize(ol)["steps"][0]["hostRequirements"],
            _expected("""
                amounts:
                  - name: amount.worker.vcpu
                    min: 16.0
                attributes:
                  - name: 'opencue:attr.tag'
                    allOf: [render, gpu]
                  - name: 'opencue:attr.service'
                    anyOf: [shell]
            """),
        )


class SerializeLimitsTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_single_limit(self):
        ol = outline.Outline("limit-job", shot="test", show="testing", user=TEST_USER)
        layer = outline.modules.shell.Shell("render", command=["render"], range="1-10")
        layer.set_limits(["nuke"])
        ol.add_layer(layer)

        self.assertEqual(
            _serialize(ol)["steps"][0]["hostRequirements"],
            _expected("""
                amounts:
                  - name: amount.limit.nuke
                    min: 1
                attributes:
                  - name: 'opencue:attr.service'
                    anyOf: [shell]
            """),
        )

    def test_multiple_limits(self):
        ol = outline.Outline("multi-limit-job", shot="test", show="testing", user=TEST_USER)
        layer = outline.modules.shell.Shell("render", command=["render"], range="1-10")
        layer.set_limits(["nuke", "katana"])
        ol.add_layer(layer)

        self.assertEqual(
            _serialize(ol)["steps"][0]["hostRequirements"],
            _expected("""
                amounts:
                  - name: amount.limit.nuke
                    min: 1
                  - name: amount.limit.katana
                    min: 1
                attributes:
                  - name: 'opencue:attr.service'
                    anyOf: [shell]
            """),
        )


class SerializeChunkingTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_chunk_size_one(self):
        ol = outline.Outline("nochunk-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell("render", command=["render", "#IFRAME#"], range="1-100")
        )

        template = _serialize(ol)
        param = template["steps"][0]["parameterSpace"]["taskParameterDefinitions"][0]
        self.assertEqual("CHUNK[INT]", param["type"])
        self.assertIn("chunk_size = 1", template["steps"][0]["let"])

    def test_chunk_size_ten(self):
        ol = outline.Outline("chunk-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell(
                "render", command=["render", "#IFRAME#"], range="1-100", chunk=10
            )
        )

        template = _serialize(ol)
        self.assertIn("chunk_size = 10", template["steps"][0]["let"])

    def test_chunk_with_framespec(self):
        """#FRAMESPEC# maps to Task.Param.Frame directly in the wrapper."""
        ol = outline.Outline("framespec-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell(
                "render",
                command=["render", "--frames", "#FRAMESPEC#"],
                range="1-100",
                chunk=10,
            )
        )

        wrapper = _wrapper_data(_serialize(ol)["steps"][0])
        self.assertIn("'{{ Task.Param.Frame }}'", wrapper)

    def test_chunk_with_start_end(self):
        """#FRAME_START# and #FRAME_END# use min()/max() in the wrapper."""
        ol = outline.Outline("startend-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell(
                "render",
                command=["render", "-start", "#FRAME_START#", "-end", "#FRAME_END#"],
                range="1-100",
                chunk=10,
            )
        )

        wrapper = _wrapper_data(_serialize(ol)["steps"][0])
        self.assertIn("'{{ min(Task.Param.Frame) }}'", wrapper)
        self.assertIn("'{{ max(Task.Param.Frame) }}'", wrapper)


class SerializePostLayerTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_post_depends_on_all(self):
        ol = outline.Outline("post-job", shot="test", show="testing", user=TEST_USER)
        ol.add_layer(
            outline.modules.shell.Shell("render", command=["render", "#IFRAME#"], range="1-100")
        )
        ol.add_layer(
            outline.modules.shell.Shell("composite", command=["comp", "#IFRAME#"], range="1-100")
        )
        ol.add_layer(
            outline.modules.shell.Shell("cleanup", command=["cleanup"], range="1-1", type="Post")
        )

        template = _serialize(ol)
        self.assertEqual(3, len(template["steps"]))
        self.assertNotIn("dependencies", template["steps"][0])
        self.assertNotIn("dependencies", template["steps"][1])

        cleanup = template["steps"][2]
        dep_names = {d["dependsOn"] for d in cleanup["dependencies"]}
        self.assertEqual({"render", "composite"}, dep_names)

    def test_post_merges_explicit_and_implicit_deps(self):
        ol = outline.Outline("post-merge-job", shot="test", show="testing", user=TEST_USER)
        r = outline.modules.shell.Shell("render", command=["render"], range="1-10")
        ol.add_layer(r)
        n = outline.modules.shell.Shell("notify", command=["notify"], range="1-1", type="Post")
        n.depend_all(r)
        ol.add_layer(n)

        template = _serialize(ol)
        self.assertEqual(template["steps"][1]["dependencies"], [{"dependsOn": "render"}])


class SerializeShellScriptTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_shell_script_embeds_file(self):
        ol = outline.Outline("script-job", shot="test", show="testing", user=TEST_USER)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, encoding="utf-8"
        ) as f:
            f.write("#!/bin/bash\necho hello $1\n")
            script_path = f.name

        try:
            layer = outline.modules.shell.ShellScript("run-script", script=script_path)
            ol.add_layer(layer)

            template = _serialize(ol)
            step = template["steps"][0]

            # Script file is embedded
            script_ef = next(ef for ef in step["script"]["embeddedFiles"] if ef["name"] == "script")
            self.assertTrue(script_ef["runnable"])
            self.assertEqual("#!/bin/bash\necho hello $1\n", script_ef["data"])

            # Wrapper calls the script via repr_sh
            wrapper = _wrapper_data(step)
            self.assertIn("{{ repr_sh(Task.File.script) }}", wrapper)
            self.assertIn(WRAPPER_PREAMBLE, wrapper)
        finally:
            os.unlink(script_path)


class SerializePyEvalTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_pyeval_embeds_code(self):
        ol = outline.Outline("pyeval-job", shot="test", show="testing", user=TEST_USER)
        code = "import os\nprint(os.getcwd())\n"
        layer = outline.modules.shell.PyEval("run-python", code=code, range="1-1")
        ol.add_layer(layer)

        template = _serialize(ol)
        step = template["steps"][0]

        # Code is embedded without shebang, not runnable
        script_ef = next(ef for ef in step["script"]["embeddedFiles"] if ef["name"] == "script")
        self.assertNotIn("runnable", script_ef)
        self.assertEqual(code, script_ef["data"])

        # Wrapper calls python on the script via repr_sh
        wrapper = _wrapper_data(step)
        self.assertIn("python {{ repr_sh(Task.File.script) }}", wrapper)
        self.assertIn(WRAPPER_PREAMBLE, wrapper)


class SerializeStringCommandTest(unittest.TestCase):
    def setUp(self):
        outline.Outline.current = None

    def test_string_command_is_split(self):
        """A string command should be shlex.split like PyOutline does at runtime."""
        ol = outline.Outline("str-cmd-job", shot="test", show="testing", user=TEST_USER)
        layer = outline.modules.shell.Shell("render", range="1-10")
        layer.set_arg("command", "render -start #IFRAME# -end #IFRAME#")
        ol.add_layer(layer)

        wrapper = _wrapper_data(_serialize(ol)["steps"][0])
        self.assertIn("render", wrapper)
        self.assertIn("'{{ min(Task.Param.Frame) }}'", wrapper)
        self.assertIn(WRAPPER_PREAMBLE, wrapper)


if __name__ == "__main__":
    unittest.main()

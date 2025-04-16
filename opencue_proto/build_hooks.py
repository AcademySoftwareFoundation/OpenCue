
"""
Custom build script for building the package
"""
import glob
import os
import re
import subprocess
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        # Compile protocol buffers
        proto_dir = os.path.join(self.root, "proto")
        output_dir = os.path.join(self.root, "opencue_proto")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        proto_files = [f for f in os.listdir(proto_dir) if f.endswith(".proto")]

        if not proto_files:
            print("No .proto files found.")
            return

        command = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I={proto_dir}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
        ] + [os.path.join(proto_dir, f) for f in proto_files]

        print(f"Compiling protocol buffers: {' '.join(command)}")
        subprocess.check_call(command)

        # Fix compiled proto imports
        pattern = re.compile(r"^import \w+ as \w+_pb2")
        for filepath in glob.glob(os.path.join(output_dir, "*_pb2*.py")):
            filedata = []
            with open(filepath) as f:
                for line in f.readlines():
                    match = pattern.match(line)
                    if match is not None:
                        line = f"from . {line}"
                    filedata.append(line.strip("\n"))
            with open(filepath, "w") as f:
                f.write("\n".join(filedata))

@hookimpl
def hatch_register_build_hook():
    return CustomBuildHook()

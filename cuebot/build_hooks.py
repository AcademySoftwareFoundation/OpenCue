
import os
import subprocess
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

class CustomBuildHook(BuildHookInterface):
#    def __init__(self):
#        #self.root = root
#        #self.config = config

    def initialize(self, version, build_data):
        # Compile protocol buffers
        proto_dir = os.path.join(self.root, "proto")
        output_dir = os.path.join(self.root, "cuebot", "proto")
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
        fix_script = os.path.join(self.root, "proto", "fix_compiled_proto.py")
        command = [sys.executable, fix_script, output_dir]
        print(f"Fixing compiled proto imports: {' '.join(command)}")
        subprocess.check_call(command)

@hookimpl
def hatch_register_build_hook():
    return CustomBuildHook()

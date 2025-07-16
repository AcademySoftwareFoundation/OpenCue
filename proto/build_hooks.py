
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
    """
    Custom Hatch build hook for compiling Protocol Buffer definitions (.proto).

    This hook integrates with the Hatch build process and is triggered
    during the initialization phase via its `initialize` method before the
    main build process begins.

    It performs the following main tasks:
    1. Locates all `.proto` files within the project's `proto/` subdirectory.
    2. Invokes the `grpc_tools.protoc` compiler to generate the corresponding
       Python modules (`_pb2.py`) and gRPC service modules (`_pb2_grpc.py`).
    3. Places the generated Python files into the `opencue_proto/`
       subdirectory, making them available for inclusion in the final package.
    4. Post-processes the generated Python files to modify imports between
       compiled proto modules, changing them from absolute (e.g., `import X_pb2`)
       to relative (e.g., `from . import X_pb2`). This ensures the generated
       code works correctly when installed as part of the `opencue_proto` package.

    This automation avoids the need to manually compile protos and commit the
    generated code to the repository.
    """
    def initialize(self, version, build_data):
        # Compile protocol buffers
        proto_dir = os.path.join(self.root, "src")
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

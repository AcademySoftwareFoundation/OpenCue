#!/usr/bin/env python

"""Script that makes the imports in the generated compiled_proto python files relative.

"""
import os
import re
import sys
import glob

PYTHON_SCRIPT_PATH = sys.argv[1]

if os.path.isdir(PYTHON_SCRIPT_PATH):
    pattern = re.compile(r"^import \w+ as \w+_pb2")
    for filepath in glob.glob(os.path.join(PYTHON_SCRIPT_PATH, "*_pb2*.py")):
        filedata = []
        with open(filepath) as f:
            for line in f.readlines():
                match = pattern.match(line)
                if match is not None:
                    line = f"from . {line}"
                filedata.append(line.strip("\n"))
        with open(filepath, "w") as f:
            f.write("\n".join(filedata))
else:
    print("Argument is not a directory")

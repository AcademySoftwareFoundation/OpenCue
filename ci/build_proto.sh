#!/bin/bash

# Protos need to have their Python code generated in order for tests to pass.
python -m grpc_tools.protoc -I=cuebot/proto/ --python_out=cuebot/cuebot/proto --grpc_python_out=cuebot/cuebot/proto cuebot/proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
python ci/fix_compiled_proto.py cuebot/cuebot/proto

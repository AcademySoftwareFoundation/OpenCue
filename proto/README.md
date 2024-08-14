# OpenCue Protobuf Files

These files define the high-level data types in OpenCue, used across components.

To use them, they must first be compiled into the native language of the component.

## Cuebot

Gradle automatically compiles these proto files, no further action is needed.

## pycue

To generate:

```sh
python -m grpc_tools.protoc -I=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto ./*.proto
2to3 -wn -f import ../pycue/opencue/compiled_proto/*_pb2*.py
```

For Windows (Powershell):

```powershell
python -m grpc_tools.protoc --proto_path=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto (ls *.proto).Name
cd ..\pycue\opencue\compiled_proto\
2to3 -wn -f import (ls *_pb2*.py).Name
```



# OpenCue Protobuf Files

These files define the high-level data types in OpenCue, used across components.

To use them, they must first be compiled into the native language of the component.

## Cuebot

Gradle automatically compiles these proto files, no further action is needed.

## RQD

To generate:

```sh
python -m grpc_tools.protoc -I=. --python_out=../rqd/rqd/compiled_proto --grpc_python_out=../rqd/rqd/compiled_proto ./*.proto
python ../ci/fix_compiled_proto.py ../rqd/rqd/compiled_proto
```

For Windows (Powershell):

```powershell
python -m grpc_tools.protoc --proto_path=. --python_out=../rqd/rqd/compiled_proto --grpc_python_out=../rqd/rqd/compiled_proto (ls *.proto).Name
python ../ci/fix_compiled_proto.py ../rqd/rqd/compiled_proto
```


## pycue

To generate:

```sh
python -m grpc_tools.protoc -I=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto ./*.proto
python ../ci/fix_compiled_proto.py ../pycue/opencue/compiled_proto
```

For Windows (Powershell):

```powershell
python -m grpc_tools.protoc --proto_path=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto (ls *.proto).Name
python ../ci/fix_compiled_proto.py ../pycue/opencue/compiled_proto
```





To generate RQD python files
python -m grpc_tools.protoc -I=. --python_out=../../../../rqd/src --grpc_python_out=../../../../rqd/src ./rqd.proto


To generate spi_cue python files
python -m grpc_tools.protoc -I=. --python_out=../../../../spi_cue/Cue3/compiled_proto --grpc_python_out=../../../../spi_cue/Cue3/compiled_proto ./*.proto


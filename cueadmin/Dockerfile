FROM python:3.9.14

WORKDIR /src

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --upgrade setuptools

COPY LICENSE ./
COPY requirements.txt ./

RUN python3 -m pip install -r requirements.txt

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/opencue ./pycue/opencue
COPY pycue/FileSequence ./pycue/FileSequence

RUN python3 -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN 2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py

COPY cueadmin/README.md ./cueadmin/
COPY cueadmin/setup.py ./cueadmin/
COPY cueadmin/tests/ ./cueadmin/tests
COPY cueadmin/cueadmin ./cueadmin/cueadmin

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

RUN cd pycue && python3 -m pip install .
RUN cd cueadmin && python3 tests/test_suite.py

RUN cp LICENSE requirements.txt VERSION cueadmin/

RUN versioned_name="cueadmin-$(cat ./VERSION)-all" \
  && mv cueadmin "${versioned_name}" \
  && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
  && mkdir -p /opt/opencue \
  && cp "${versioned_name}.tar.gz" /opt/opencue/

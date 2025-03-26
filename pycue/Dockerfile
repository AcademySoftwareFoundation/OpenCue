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
COPY pycue/FileSequence ./pycue/FileSequence
COPY pycue/tests/ ./pycue/tests
COPY pycue/opencue ./pycue/opencue

RUN python3 -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
COPY ci/fix_compiled_proto.py ./ci/
RUN python3 ci/fix_compiled_proto.py pycue/opencue/compiled_proto

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

RUN cd pycue && python3 -m pip install .
RUN cd pycue && python3 tests/test_suite.py

RUN cp LICENSE requirements.txt VERSION pycue/

RUN versioned_name="pycue-$(cat ./VERSION)-all" \
  && mv pycue "${versioned_name}" \
  && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
  && mkdir /opt/opencue \
  && cp "${versioned_name}.tar.gz" /opt/opencue/

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
RUN python ci/fix_compiled_proto.py pycue/opencue/compiled_proto

COPY pyoutline/README.md ./pyoutline/
COPY pyoutline/setup.py ./pyoutline/
COPY pyoutline/bin ./pyoutline/bin
COPY pyoutline/tests/ ./pyoutline/tests
COPY pyoutline/wrappers ./pyoutline/wrappers
COPY pyoutline/outline ./pyoutline/outline

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

# Install pycue as pyoutline depends on it to run tests
RUN cd pycue && python3 -m pip install .
RUN cd pyoutline && python3 tests/test_suite.py

RUN cp LICENSE requirements.txt VERSION pyoutline/

RUN versioned_name="pyoutline-$(cat ./VERSION)-all" \
  && mv pyoutline "${versioned_name}" \
  && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
  && mkdir -p /opt/opencue \
  && cp "${versioned_name}.tar.gz" /opt/opencue/

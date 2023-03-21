FROM --platform=linux/x86_64 centos:7

WORKDIR /src

RUN yum -y install \
  epel-release \
  gcc \
  mesa-libGL \
  python-devel

RUN yum -y install \
  python36 \
  python36-devel \
  python36-pip

RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install --upgrade setuptools

COPY LICENSE ./
COPY requirements.txt ./
COPY requirements_gui.txt ./

RUN python3.6 -m pip install -r requirements.txt -r requirements_gui.txt

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/opencue ./pycue/opencue
COPY pycue/FileSequence ./pycue/FileSequence

RUN python3.6 -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN 2to3 -wn -f import pycue/opencue/compiled_proto/*_pb2*.py

COPY pyoutline/README.md ./pyoutline/
COPY pyoutline/setup.py ./pyoutline/
COPY pyoutline/bin ./pyoutline/bin
COPY pyoutline/wrappers ./pyoutline/wrappers
COPY pyoutline/outline ./pyoutline/outline

COPY cuesubmit/README.md ./cuesubmit/
COPY cuesubmit/setup.py ./cuesubmit/
COPY cuesubmit/tests/ ./cuesubmit/tests
COPY cuesubmit/plugins ./cuesubmit/plugins
COPY cuesubmit/cuesubmit ./cuesubmit/cuesubmit

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

RUN cd pycue && python3.6 setup.py install
RUN cd pyoutline && python3.6 setup.py install
RUN cd cuesubmit && python3.6 setup.py test

RUN cp LICENSE requirements.txt requirements_gui.txt VERSION cuesubmit/

RUN versioned_name="cuesubmit-$(cat ./VERSION)-all" \
  && mv cuesubmit "${versioned_name}" \
  && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
  && mkdir -p /opt/opencue \
  && cp "${versioned_name}.tar.gz" /opt/opencue/

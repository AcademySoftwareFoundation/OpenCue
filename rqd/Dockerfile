FROM centos:7

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install \
  python-pip \
  python36 \
  python36-devel \
  python36-pip

RUN pip install --upgrade setuptools
RUN pip3.6 install --upgrade setuptools

WORKDIR /opt/opencue

COPY LICENSE ./
COPY requirements.txt ./

RUN pip install -r requirements.txt
RUN pip3.6 install -r requirements.txt

COPY proto/ ./proto
COPY rqd/deploy ./rqd/deploy
COPY rqd/README.md ./rqd/
COPY rqd/setup.py ./rqd/
COPY rqd/tests/ ./rqd/tests
COPY rqd/rqd/ ./rqd/rqd

RUN python3.6 -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./rqd/rqd/compiled_proto \
  --grpc_python_out=./rqd/rqd/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN sed -i 's/^\(import.*_pb2\)/from . \1/' rqd/rqd/compiled_proto/*.py

# TODO(bcipriano) Lint the code here. (Issue #78)

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

# Test in Python 2 and 3, but only install in the Python 3 environment.
RUN cd rqd && python setup.py test
RUN cd rqd && python3.6 setup.py test
RUN cd rqd && python3.6 setup.py install

# This step isn't really needed at runtime, but is used when publishing an OpenCue release
# from this build.
RUN versioned_name="rqd-$(cat ./VERSION)-all" \
  && cp LICENSE requirements.txt VERSION rqd/ \
  && mv rqd $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/* \
  && ln -s $versioned_name rqd

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]

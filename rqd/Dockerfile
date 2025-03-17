FROM rockylinux:8.9

WORKDIR /opt/opencue

RUN yum -y install \
  epel-release \
  gcc \
  time

RUN dnf install -y \
  python39 \
  python39-devel \
  python39-pip

RUN python3.9 -m pip install --upgrade pip
RUN python3.9 -m pip install --upgrade setuptools

COPY LICENSE ./

COPY cuebot/cuebot ./cuebot/cuebot
COPY cuebot/proto ./cuebot/proto
COPY cuebot/pyproject.toml ./cuebot/

COPY ci/fix_compiled_proto.py ./ci/

# Install dependencies for cuebot
RUN python3.9 -m pip install ./cuebot
# Compile proto files
RUN python3.9 -m grpc_tools.protoc \
    -I=cuebot/proto/ \
    --python_out=cuebot/cuebot/proto \
    --grpc_python_out=cuebot/cuebot/proto \
    cuebot/proto/*.proto
# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN python3.9 ci/fix_compiled_proto.py cuebot/cuebot/proto

# Install package with compiled proto files
RUN python3.9 -m pip install ./cuebot

COPY rqd/deploy ./rqd/deploy
COPY rqd/README.md ./rqd/
COPY rqd/pyproject.toml ./rqd/
COPY rqd/tests/ ./rqd/tests
COPY rqd/rqd/ ./rqd/rqd

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

RUN cd rqd && python3.9 -m pip install .
RUN cd rqd && python3.9 -m unittest discover

# This step isn't really needed at runtime, but is used when publishing an OpenCue release
# from this build.
# Disable this for for better future packaging
#RUN versioned_name="rqd-$(cat ./VERSION)-all" \
#  && cp LICENSE VERSION rqd/ \
#  && mv rqd $versioned_name \
#  && tar -cvzf $versioned_name.tar.gz $versioned_name/* \
#  && ln -s $versioned_name rqd

RUN mkdir -p /etc/opencue
RUN echo "[Override]" > /etc/opencue/rqd.conf
RUN echo "USE_NIMBY_PYNPUT=false" >> /etc/opencue/rqd.conf

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]

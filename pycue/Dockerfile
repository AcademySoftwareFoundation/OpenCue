FROM centos:7 as base

# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /src

RUN yum -y install \
  epel-release \
  gcc \
  python-devel

# TODO remove
RUN yum -y install vim

RUN yum -y install python-pip

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/Cue3 ./pycue/Cue3
COPY pycue/FileSequence ./pycue/FileSequence

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/Cue3/compiled_proto \
  --grpc_python_out=./pycue/Cue3/compiled_proto \
  ./proto/*.proto

# TODO(cipriano) Lint the code here. (b/121159562)


# -----------------
# TEST
# -----------------
FROM build as test


# -----------------
# PACKAGE
# -----------------
FROM build as package


# -----------------
# RUN
# -----------------
FROM base


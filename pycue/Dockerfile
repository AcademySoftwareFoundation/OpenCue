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

COPY pycue/tests/ ./pycue/tests

# TODO(cipriano) Run unit tests.


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt pycue/

# TODO(cipriano) Make version number dynamic. (b/121159512)
RUN tar -cvzf pycue-0.1-all.tar.gz pycue/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

COPY --from=package /src/pycue-0.1-all.tar.gz ./


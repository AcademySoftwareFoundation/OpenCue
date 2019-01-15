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

RUN yum -y install python-pip

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY VERSION ./
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

RUN cp requirements.txt VERSION pycue/

RUN versioned_name="pycue-$(cat ./VERSION)-all" \
  && mv pycue $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/opencue

COPY --from=package /src/pycue-*-all.tar.gz ./


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

RUN yum -y install \
  python-pip \
  python36 \
  python36-devel \
  python36-pip

COPY requirements.txt ./

RUN pip install -r requirements.txt

RUN pip3.6 install -r requirements.txt

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/opencue ./pycue/opencue
COPY pycue/FileSequence ./pycue/FileSequence

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN sed -i 's/^\(import.*_pb2\)/from . \1/' pycue/opencue/compiled_proto/*.py

RUN cd pycue && python setup.py install

RUN cd pycue && python3.6 setup.py install

COPY cueadmin/README.md ./cueadmin/
COPY cueadmin/setup.py ./cueadmin/
COPY cueadmin/cueadmin ./cueadmin/cueadmin

# TODO(bcipriano) Lint the code here. (Issue #78)


# -----------------
# TEST
# -----------------
FROM build as test

COPY cueadmin/tests/ ./cueadmin/tests

RUN cd cueadmin && python setup.py test

RUN cd cueadmin && python3.6 setup.py test


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt VERSION cueadmin/

RUN versioned_name="cueadmin-$(cat ./VERSION)-all" \
  && mv cueadmin $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/opencue

COPY --from=package /src/cueadmin-*-all.tar.gz ./


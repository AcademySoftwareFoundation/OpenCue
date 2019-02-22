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

COPY cuegui/README.md ./cuegui/
COPY cuegui/setup.py ./cuegui/
COPY cuegui/cuegui ./cuegui/cuegui

# TODO(bcipriano) Lint the code here. (Issue #78)


# -----------------
# TEST
# -----------------
FROM build as test

# TODO(bcipriano) Run unit tests. (Issue #149)


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt VERSION cuegui/

RUN versioned_name="cuegui-$(cat ./VERSION)-all" \
  && mv cuegui $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/opencue

COPY --from=package /src/cuegui-*-all.tar.gz ./


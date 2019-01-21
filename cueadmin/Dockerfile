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

RUN cd pycue && python setup.py install

COPY cueadmin/README.md ./cueadmin/
COPY cueadmin/setup.py ./cueadmin/
COPY cueadmin/cueadmin ./cueadmin/cueadmin

# TODO(bcipriano) Lint the code here.
# https://github.com/imageworks/OpenCue/issues/78


# -----------------
# TEST
# -----------------
FROM build as test

# TODO(bcipriano) Run unit tests.


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


FROM centos:7 as base

# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /src

RUN yum -y install \
  epel-release \
  gcc \
  mesa-libGL \
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

COPY pyoutline/README.md ./pyoutline/
COPY pyoutline/setup.py ./pyoutline/
COPY pyoutline/bin ./pyoutline/bin
COPY pyoutline/etc ./pyoutline/etc
COPY pyoutline/wrappers ./pyoutline/wrappers
COPY pyoutline/outline ./pyoutline/outline

RUN cd pyoutline && python setup.py install

COPY cuesubmit/README.md ./cuesubmit/
COPY cuesubmit/setup.py ./cuesubmit/
COPY cuesubmit/plugins ./cuesubmit/plugins
COPY cuesubmit/cuesubmit ./cuesubmit/cuesubmit

# TODO(bcipriano) Lint the code here. (Issue #78)


# -----------------
# TEST
# -----------------
FROM build as test

COPY cuesubmit/tests/ ./cuesubmit/tests

RUN cd cuesubmit && python setup.py test


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt VERSION cuesubmit/

RUN versioned_name="cuesubmit-$(cat ./VERSION)-all" \
  && mv cuesubmit $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/opencue

COPY --from=package /src/cuesubmit-*-all.tar.gz ./


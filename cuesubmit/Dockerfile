# -----------------
# BUILD
# -----------------
FROM centos:7 as build

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "CueSubmit build stage"

WORKDIR /src

RUN yum -y install \
  epel-release \
  gcc \
  mesa-libGL \
  python-devel

RUN yum -y install \
  python-pip \
  python36 \
  python36-devel \
  python36-pip

COPY LICENSE ./
COPY requirements.txt ./
COPY requirements_gui.txt ./

RUN pip install -r requirements.txt -r requirements_gui.txt

RUN pip3.6 install -r requirements.txt -r requirements_gui.txt

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

COPY pyoutline/README.md ./pyoutline/
COPY pyoutline/setup.py ./pyoutline/
COPY pyoutline/bin ./pyoutline/bin
COPY pyoutline/etc ./pyoutline/etc
COPY pyoutline/wrappers ./pyoutline/wrappers
COPY pyoutline/outline ./pyoutline/outline

COPY cuesubmit/README.md ./cuesubmit/
COPY cuesubmit/setup.py ./cuesubmit/
COPY cuesubmit/tests/ ./cuesubmit/tests
COPY cuesubmit/plugins ./cuesubmit/plugins
COPY cuesubmit/cuesubmit ./cuesubmit/cuesubmit

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

RUN cd pycue && python setup.py install

RUN cd pycue && python3.6 setup.py install

RUN cd pyoutline && python setup.py install

RUN cd pyoutline && python3.6 setup.py install

# TODO(bcipriano) Lint the code here. (Issue #78)

RUN cd cuesubmit && python setup.py test

RUN cd cuesubmit && python3.6 setup.py test

RUN cp LICENSE requirements.txt requirements_gui.txt VERSION cuesubmit/

RUN versioned_name="cuesubmit-$(cat ./VERSION)-all" \
  && mv cuesubmit $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM centos:7

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "CueSubmit runtime stage"

WORKDIR /opt/opencue

COPY --from=build /src/cuesubmit-*-all.tar.gz ./


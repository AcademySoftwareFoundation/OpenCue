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

RUN yum -y install python-pip

COPY LICENSE ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

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

RUN cd pyoutline && python setup.py install

# TODO(bcipriano) Lint the code here. (Issue #78)

RUN cd cuesubmit && python setup.py test

RUN cp LICENSE requirements.txt VERSION cuesubmit/

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


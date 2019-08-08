# -----------------
# BUILD
# -----------------
FROM centos:7 as build

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "CueAdmin build stage"

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

COPY LICENSE ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

RUN pip3.6 install -r requirements.txt

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

COPY cueadmin/README.md ./cueadmin/
COPY cueadmin/setup.py ./cueadmin/
COPY cueadmin/tests/ ./cueadmin/tests
COPY cueadmin/cueadmin ./cueadmin/cueadmin

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

RUN cd pycue && python setup.py install

RUN cd pycue && python3.6 setup.py install

# TODO(bcipriano) Lint the code here. (Issue #78)

RUN cd cueadmin && python setup.py test

RUN cd cueadmin && python3.6 setup.py test

RUN cp LICENSE requirements.txt VERSION cueadmin/

RUN versioned_name="cueadmin-$(cat ./VERSION)-all" \
  && mv cueadmin $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM centos:7

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "CueAdmin runtime stage"

WORKDIR /opt/opencue

COPY --from=build /src/cueadmin-*-all.tar.gz ./


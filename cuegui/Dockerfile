# -----------------
# BUILD
# -----------------
FROM centos:7 as build

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "CueGUI build stage"

WORKDIR /src

RUN yum -y install \
  epel-release \
  fontconfig \
  freetype \
  gcc \
  libXi \
  libXrender \
  mesa-libGL \
  python-devel \
  which \
  Xvfb

RUN yum -y install \
  python-pip \
  python36 \
  python36-devel \
  python36-pip

RUN dbus-uuidgen > /etc/machine-id

COPY LICENSE ./
COPY requirements.txt ./
COPY requirements_gui.txt ./

RUN pip install -r requirements.txt -r requirements_gui.txt

RUN pip3.6 install -r requirements.txt -r requirements_gui.txt

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/FileSequence ./pycue/FileSequence
COPY pycue/opencue ./pycue/opencue

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN sed -i 's/^\(import.*_pb2\)/from . \1/' pycue/opencue/compiled_proto/*.py

COPY cuegui/README.md ./cuegui/
COPY cuegui/setup.py ./cuegui/
COPY cuegui/tests ./cuegui/tests
COPY cuegui/cuegui ./cuegui/cuegui

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

RUN cd pycue && python setup.py install

RUN cd pycue && python3.6 setup.py install

# TODO(bcipriano) Lint the code here. (Issue #78)

RUN cd cuegui && xvfb-run -d python setup.py test

RUN cd cuegui && xvfb-run -d python3.6 setup.py test

RUN cp LICENSE requirements.txt requirements_gui.txt VERSION cuegui/

RUN versioned_name="cuegui-$(cat ./VERSION)-all" \
  && mv cuegui $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM centos:7

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "CueGUI runtime stage"

WORKDIR /opt/opencue

COPY --from=build /src/cuegui-*-all.tar.gz ./


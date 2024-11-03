FROM --platform=linux/x86_64 centos:7

WORKDIR /src

# centos:7 repos moved to vault.centos
RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/CentOS-*.repo
RUN sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/CentOS-*.repo
RUN sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/CentOS-*.repo

RUN yum -y install \
  epel-release \
  fontconfig \
  freetype \
  gcc \
  libXi \
  libXrender \
  libxkbcommon-x11.x86_64 \
  mesa-libGL \
  python-devel \
  which \
  Xvfb \
  xcb-util-image.x86_64 \
  xcb-util-keysyms.x86_64 \
  xcb-util-renderutil.x86_64 \
  xcb-util-wm.x86_64

RUN yum -y install \
  python36 \
  python36-devel \
  python36-pip

RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install --upgrade setuptools

RUN dbus-uuidgen > /etc/machine-id

COPY LICENSE ./
COPY requirements.txt ./
COPY requirements_gui.txt ./

RUN python3.6 -m pip install -r requirements.txt -r requirements_gui.txt

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/FileSequence ./pycue/FileSequence
COPY pycue/opencue ./pycue/opencue

RUN python3.6 -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN python3 ci/fix_compiled_proto.py pycue/opencue/compiled_proto

COPY cuegui/README.md ./cuegui/
COPY cuegui/setup.py ./cuegui/
COPY cuegui/tests ./cuegui/tests
COPY cuegui/cuegui ./cuegui/cuegui

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

RUN cd pycue && python3.6 setup.py install

RUN cd cuegui && xvfb-run -d python3.6 setup.py test

RUN cp LICENSE requirements.txt requirements_gui.txt VERSION cuegui/

RUN versioned_name="cuegui-$(cat ./VERSION)-all" \
  && mv cuegui "${versioned_name}" \
  && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
  && mkdir -p /opt/opencue \
  && cp "${versioned_name}.tar.gz" /opt/opencue/

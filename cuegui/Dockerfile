FROM --platform=linux/x86_64 rockylinux:9.3

WORKDIR /src

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
    python\
    python-pip

RUN python -m pip install --upgrade pip

COPY LICENSE requirements.txt requirements_gui.txt ./
RUN python -m pip install -r requirements.txt -r requirements_gui.txt

COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/FileSequence ./pycue/FileSequence
COPY pycue/opencue ./pycue/opencue
COPY ci/fix_compiled_proto.py .

RUN python -m grpc_tools.protoc \
    -I=./proto \
    --python_out=./pycue/opencue/compiled_proto \
    --grpc_python_out=./pycue/opencue/compiled_proto \
    ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN python ./fix_compiled_proto.py pycue/opencue/compiled_proto

COPY cuegui/README.md ./cuegui/
COPY cuegui/setup.py ./cuegui/
COPY cuegui/tests ./cuegui/tests
COPY cuegui/cuegui ./cuegui/cuegui

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

RUN cd pycue && python setup.py install
RUN cd cuegui && xvfb-run -d python setup.py test
RUN cp LICENSE requirements.txt requirements_gui.txt VERSION cuegui/

RUN versioned_name="cuegui-$(cat ./VERSION)-all" \
    && mv cuegui "${versioned_name}" \
    && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
    && mkdir -p /opt/opencue \
    && cp "${versioned_name}.tar.gz" /opt/opencue/

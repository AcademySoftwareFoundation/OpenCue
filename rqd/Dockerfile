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

# TODO(cipriano) Remove PySide for now. It's not needed for RQD anyway.
RUN sed -i '/^PySide/ d' requirements.txt

RUN pip install -r requirements.txt

COPY proto/ ./proto
COPY rqd/rqd/ ./rqd
COPY rqd/setup.py ./

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./rqd/compiled_proto \
  --grpc_python_out=./rqd/compiled_proto \
  ./proto/*.proto

# TODO(cipriano) Lint the code here. (b/)


# -----------------
# TEST
# -----------------
FROM build as test

COPY rqd/rqd/test/ ./rqd/test

RUN rqd/unittests.py


# -----------------
# PACKAGE
# -----------------
FROM build as package

# We use Platter here to build a self-contained installer, but if you'd rather have
# a systemwide install you can also just do `python setup.py install`. This adds a
# `rqd` launcher script to your PATH.

RUN pip install platter
RUN platter build -r requirements.txt .


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

# TODO(cipriano) Make version number dynamic. (b/)

COPY --from=package /src/dist/rqd-0.1-linux-x86_64.tar.gz ./

RUN tar -xvzf rqd-0.1-linux-x86_64.tar.gz

RUN ./rqd-0.1-linux-x86_64/install.sh ./rqd

ENTRYPOINT ["/opt/cue3/rqd/bin/rqd"]


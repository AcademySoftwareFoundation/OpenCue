FROM centos:7 as base

# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /src

COPY requirements.txt ./
RUN sed -i '/^PySide/ d' requirements.txt
COPY rqd/rqd/ ./rqd
COPY rqd/setup.py ./

# TODO: lint the code here


# -----------------
# TEST
# -----------------
FROM build as test

# TODO: run tests here


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN yum -y install \
  epel-release \
  gcc \
  python-devel

RUN yum -y install python-pip

RUN pip install pex wheel

# RUN pip wheel --no-cache-dir --wheel-dir=./wheels -r requirements.txt
RUN pip wheel -w . .

RUN pex -f /src -r requirements.txt rqd -e rqd.__main__ -o rqd.pex


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

COPY --from=package /src/rqd.pex /opt/cue3/rqd.pex

ENTRYPOINT ["/opt/cue3/rqd.pex"]


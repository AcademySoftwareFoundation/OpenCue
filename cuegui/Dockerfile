ARG upstream_version=latest

FROM opencue/pycue:${upstream_version} as base

# -----------------
# BUILD
# -----------------
FROM base as build

ARG upstream_version

RUN yum -y install \
  epel-release \
  gcc \
  python-devel

RUN yum -y install python-pip

WORKDIR /src

COPY VERSION ./

# If an upstream version was specified make sure it matches what's in the code.
RUN test "${upstream_version}" == "latest" || test "${upstream_version}" = "$(cat ./VERSION)"

WORKDIR /opt/cue3

RUN tar -xvzf pycue-$(cat /src/VERSION)-all.tar.gz

RUN pip install -r pycue/requirements.txt

RUN cd pycue && python setup.py install

WORKDIR /src

COPY requirements.txt ./
COPY cuegui/README.md ./cuegui/
COPY cuegui/setup.py ./cuegui/
COPY cuegui/cuegui ./cuegui/cuegui

# TODO(cipriano) Lint the code here. (b/121159562)


# -----------------
# TEST
# -----------------
FROM build as test

# TODO(cipriano) Run unit tests.


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt VERSION cuegui/

RUN tar -cvzf cuegui-$(cat ./VERSION)-all.tar.gz cuegui/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

COPY --from=package /src/cuegui-*-all.tar.gz ./


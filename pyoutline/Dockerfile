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

RUN pip install -r requirements.txt

COPY VERSION ./
COPY pyoutline/README.md ./pyoutline/
COPY pyoutline/setup.py ./pyoutline/
COPY pyoutline/src ./pyoutline/src

# TODO(bcipriano) Lint the code here.
# https://github.com/imageworks/OpenCue/issues/78


# -----------------
# TEST
# -----------------
FROM build as test

COPY pyoutline/tests/ ./pyoutline/tests

# TODO(bcipriano) Run unit tests.


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt VERSION pyoutline/

RUN versioned_name="pyoutline-$(cat ./VERSION)-all" \
  && mv pycue $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/opencue

COPY --from=package /src/pyoutline-*-all.tar.gz ./


FROM centos:7 as base

RUN yum -y install \
  epel-release \
  gcc \
  python-devel

RUN yum -y install python-pip


# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /src

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY VERSION ./
COPY proto/ ./proto
COPY rqd/deploy ./rqd/deploy
COPY rqd/README.md ./rqd/
COPY rqd/setup.py ./rqd/
COPY rqd/rqd/ ./rqd/rqd

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./rqd/rqd/compiled_proto \
  --grpc_python_out=./rqd/rqd/compiled_proto \
  ./proto/*.proto

# TODO(cipriano) Lint the code here. (b/121159562)


# -----------------
# TEST
# -----------------
FROM build as test

COPY rqd/rqd/test/ ./rqd/rqd/test

RUN rqd/rqd/unittests.py


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN mkdir dist

RUN cp rqd/deploy/install_and_run.sh dist/

RUN cp requirements.txt VERSION rqd/

RUN versioned_name="rqd-$(cat ./VERSION)-all" \
  && mv rqd dist/$versioned_name \
  && cd dist \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

COPY --from=package /src/dist/rqd-*-all.tar.gz ./
COPY --from=package /src/dist/install_and_run.sh ./
RUN chmod +x ./install_and_run.sh

ENTRYPOINT ["/opt/cue3/install_and_run.sh"]


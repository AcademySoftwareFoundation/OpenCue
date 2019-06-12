FROM centos:7 as base

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install python-pip


# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /src

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

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

# TODO(bcipriano) Lint the code here. (Issue #78)


# -----------------
# TEST
# -----------------
FROM build as test

COPY rqd/tests/ ./rqd/tests

RUN cd rqd && python setup.py test


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

WORKDIR /opt/opencue

COPY --from=package /src/dist/rqd-*-all.tar.gz ./
COPY --from=package /src/dist/install_and_run.sh ./
RUN chmod +x ./install_and_run.sh

# RQD gRPC server
EXPOSE 8444

ENTRYPOINT ["/opt/opencue/install_and_run.sh"]


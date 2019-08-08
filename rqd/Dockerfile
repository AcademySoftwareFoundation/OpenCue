# -----------------
# BUILD
# -----------------
FROM centos:7 as build

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "RQD build stage"

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install python-pip

WORKDIR /src

COPY LICENSE ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

RUN mkdir dist

COPY proto/ ./proto
COPY rqd/deploy ./rqd/deploy
COPY rqd/README.md ./rqd/
COPY rqd/setup.py ./rqd/
COPY rqd/tests/ ./rqd/tests
COPY rqd/rqd/ ./rqd/rqd

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./rqd/rqd/compiled_proto \
  --grpc_python_out=./rqd/rqd/compiled_proto \
  ./proto/*.proto

# TODO(bcipriano) Lint the code here. (Issue #78)

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)-custom" | tee VERSION

RUN cd rqd && python setup.py test

RUN cp rqd/deploy/install_and_run.sh dist/

RUN cp LICENSE requirements.txt VERSION rqd/

RUN versioned_name="rqd-$(cat ./VERSION)-all" \
  && mv rqd dist/$versioned_name \
  && cd dist \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM centos:7

# First line after FROM should be unique to avoid --cache-from weirdness.
RUN echo "RQD runtime stage"

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install python-pip

WORKDIR /opt/opencue

COPY --from=build /src/dist/rqd-*-all.tar.gz ./
COPY --from=build /src/dist/install_and_run.sh ./
RUN chmod +x ./install_and_run.sh

# RQD gRPC server
EXPOSE 8444

ENTRYPOINT ["/bin/bash", "-c", "set -e && /opt/opencue/install_and_run.sh"]

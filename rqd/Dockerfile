FROM centos:7

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install python-pip

WORKDIR /opt/opencue

COPY LICENSE ./
COPY requirements.txt ./

RUN pip install -r requirements.txt

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

RUN cd rqd && python setup.py install

# This step isn't really needed at runtime, but is used when publishing an OpenCue release
# from this build.
RUN versioned_name="rqd-$(cat ./VERSION)-all" \
  && cp LICENSE requirements.txt VERSION rqd/ \
  && mv rqd $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/* \
  && ln -s $versioned_name rqd

# RQD gRPC server
EXPOSE 8444

ENTRYPOINT ["rqd"]

FROM centos:7
ENV PYTHONUNBUFFERED 1

WORKDIR /opt/opencue

# centos:7 repos moved to vault.centos
RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/CentOS-*.repo
RUN sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/CentOS-*.repo
RUN sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/CentOS-*.repo

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install \
  python-pip \
  python36 \
  python36-devel \
  python36-pip

RUN python -m pip install --upgrade 'pip<21'
RUN python3.6 -m pip install --upgrade pip

RUN python -m pip install --upgrade 'setuptools<45'
RUN python3.6 -m pip install --upgrade setuptools

COPY LICENSE ./
COPY requirements.txt ./
COPY connectors/prometheus_metrics/requirements_metrics.txt ./

RUN python -m pip install -r requirements.txt -r requirements_metrics.txt
RUN python3.6 -m pip install -r requirements.txt -r requirements_metrics.txt

COPY connectors/prometheus_metrics/metrics ./metrics
COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/FileSequence ./pycue/FileSequence
COPY pycue/opencue ./pycue/opencue

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./pycue/opencue/compiled_proto \
  --grpc_python_out=./pycue/opencue/compiled_proto \
  ./proto/*.proto

# Fix imports to work in both Python 2 and 3. See
# <https://github.com/protocolbuffers/protobuf/issues/1491> for more info.
RUN python3 ci/fix_compiled_proto.py pycue/opencue/compiled_proto

RUN cd pycue && python setup.py install

RUN cd pycue && python3.6 setup.py install

ENTRYPOINT ["python3", "/opt/opencue/metrics"]

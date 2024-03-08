FROM nvidia/cudagl:10.2-base-centos7

WORKDIR /opt/opencue

RUN yum -y install \
  epel-release \
  gcc \
  python-devel \
  time

RUN yum -y install \
  python36 \
  python36-devel \
  python36-pip

RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install --upgrade setuptools

COPY --from=opencue/rqd /opt/opencue/rqd-*-all.tar.gz /opt/opencue/
COPY --from=opencue/rqd /opt/opencue/proto/ /opt/opencue/proto/

RUN mkdir -p /etc/opencue
COPY --from=opencue/rqd /etc/opencue/rqd.conf /etc/opencue/rqd.conf

RUN tar -xvf /opt/opencue/rqd-*-all.tar.gz --strip-components=1

RUN python3.6 -m pip install -r requirements.txt

RUN python3.6 setup.py test
RUN python3.6 setup.py install

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]


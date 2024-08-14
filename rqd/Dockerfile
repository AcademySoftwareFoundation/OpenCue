FROM rockylinux:8.9

WORKDIR /opt/opencue

RUN yum -y install \
  epel-release \
  gcc \
  time

RUN dnf install -y \
  python39 \
  python39-devel \
  python39-pip

RUN python3.9 -m pip install --upgrade pip
RUN python3.9 -m pip install --upgrade setuptools

COPY LICENSE ./
COPY requirements.txt ./

RUN python3.9 -m pip install -r requirements.txt

COPY proto/ ./proto
COPY rqd/deploy ./rqd/deploy
COPY rqd/README.md ./rqd/
COPY rqd/setup.py ./rqd/
COPY rqd/tests/ ./rqd/tests
COPY rqd/rqd/ ./rqd/rqd

COPY VERSION.in VERSIO[N] ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

RUN cd rqd && python3.9 -m unittest discover
RUN cd rqd && python3.9 -m pip install .

# This step isn't really needed at runtime, but is used when publishing an OpenCue release
# from this build.
RUN versioned_name="rqd-$(cat ./VERSION)-all" \
  && cp LICENSE requirements.txt VERSION rqd/ \
  && mv rqd $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/* \
  && ln -s $versioned_name rqd

RUN mkdir -p /etc/opencue
RUN echo "[Override]" > /etc/opencue/rqd.conf
RUN echo "USE_NIMBY_PYNPUT=false" >> /etc/opencue/rqd.conf

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]

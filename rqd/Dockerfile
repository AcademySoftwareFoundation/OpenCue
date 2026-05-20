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

COPY LICENSE ./

# Copy source packages needed by rqd to execute frames.
# pyoutline provides wrappers/ (opencue_wrap_frame) and bin/ (pycuerun)
# which rqd needs to launch and execute frames.
COPY VERSION.in /tmp/opencue-src/
COPY proto/ /tmp/opencue-src/proto/
COPY pycue/ /tmp/opencue-src/pycue/
COPY pyoutline/ /tmp/opencue-src/pyoutline/
COPY rqd/ /tmp/opencue-src/rqd/

# ci/generate_version_number.py is excluded by .dockerignore.
# Create a stub that defines __version__ so hatchling can resolve the version.
RUN mkdir -p /tmp/opencue-src/ci && \
    echo '__version__ = "0.0.0"' > /tmp/opencue-src/ci/generate_version_number.py

RUN cd /tmp/opencue-src && \
    python3.9 -m pip install proto/ pycue/ pyoutline/ rqd/ && \
    rm -rf /tmp/opencue-src

# Replace tcsh-based wrappers with bash sandbox versions.
# The default opencue_wrap_frame requires /bin/tcsh and studio tools (setshot)
# which are not available in this container.
RUN WRAPPER_DIR=$(python3.9 -c "import outline; import os; print(os.path.join(os.path.dirname(os.path.dirname(outline.__file__)), 'wrappers'))") && \
    cp "$WRAPPER_DIR/opencue_wrap_frame_sandbox" "$WRAPPER_DIR/opencue_wrap_frame" && \
    chmod +x "$WRAPPER_DIR/opencue_wrap_frame"

# bin/pycuerun uses #!/usr/bin/env python but only python3.9 is installed
RUN ln -s /usr/bin/python3.9 /usr/local/bin/python

RUN mkdir -p /etc/opencue
RUN echo "[Override]" > /etc/opencue/rqd.conf
RUN echo "USE_NIMBY_PYNPUT=false" >> /etc/opencue/rqd.conf

# RQD gRPC server
EXPOSE 8444

# NOTE: This shell out is needed to avoid RQD getting PID 0 which leads to leaking child processes.
ENTRYPOINT ["/bin/bash", "-c", "set -e && rqd"]

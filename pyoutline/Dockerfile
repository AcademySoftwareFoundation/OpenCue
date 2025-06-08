FROM python:3.9

WORKDIR /opt/opencue

ARG OPENCUE_PROTO_PACKAGE_PATH
ARG OPENCUE_PYCUE_PACKAGE_PATH
ARG OPENCUE_PYOUTLINE_PACKAGE_PATH

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --upgrade setuptools

COPY LICENSE ./


COPY proto/ ./proto
COPY pycue/README.md ./pycue/
COPY pycue/setup.py ./pycue/
COPY pycue/opencue ./pycue/opencue
COPY pycue/FileSequence ./pycue/FileSequence

COPY pyoutline/README.md ./pyoutline/
COPY pyoutline/setup.py ./pyoutline/
COPY pyoutline/bin ./pyoutline/bin
COPY pyoutline/tests/ ./pyoutline/tests
COPY pyoutline/wrappers ./pyoutline/wrappers
COPY pyoutline/outline ./pyoutline/outline

COPY VERSION.in ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

# Install pycue as pyoutline depends on it to run tests
RUN python3 -m pip install ./pycue[test]
RUN python3 tests/test_suite.py

RUN cp LICENSE requirements.txt VERSION pyoutline/

RUN versioned_name="pyoutline-$(cat ./VERSION)-all" \
  && mv pyoutline "${versioned_name}" \
  && tar -cvzf "${versioned_name}.tar.gz" ${versioned_name}/* \
  && mkdir -p /opt/opencue \
  && cp "${versioned_name}.tar.gz" /opt/opencue/

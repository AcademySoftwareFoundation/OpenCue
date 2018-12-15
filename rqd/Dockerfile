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

COPY proto/ ./proto
COPY requirements.txt ./
COPY rqd/rqd/ ./rqd
COPY rqd/setup.py ./

# TODO Remove PySide for now. It's not needed for RQD anyway.
RUN sed -i '/^PySide/ d' requirements.txt

RUN pip install -r requirements.txt

RUN python -m grpc_tools.protoc \
  -I=./proto \
  --python_out=./rqd/compiled_proto \
  --grpc_python_out=./rqd/compiled_proto \
  ./proto/*.proto

# TODO: lint the code here


# -----------------
# TEST
# -----------------
FROM build as test

# TODO: run tests here


# -----------------
# PACKAGE
# -----------------
FROM build as package

#RUN pip install pex wheel
#RUN pip wheel -w . .
# RUN pip wheel --no-cache-dir --wheel-dir=./wheels -r requirements.txt
#RUN pex -f /src -r requirements.txt rqd -e rqd.__main__ -o rqd.pex

#RUN pip install virtualenv
#RUN virtualenv venv
#RUN source venv/bin/activate && pip install platter && pip install -r requirements.txt && platter build ./rqd

RUN pip install platter
RUN platter build -r requirements.txt .



# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

#COPY --from=package /src/rqd.pex /opt/cue3/rqd.pex

COPY --from=package /src/dist/rqd-0.1-linux-x86_64.tar.gz ./

RUN tar -xvzf rqd-0.1-linux-x86_64.tar.gz

RUN ./rqd-0.1-linux-x86_64/install.sh ./rqd

ENTRYPOINT ["/opt/cue3/rqd/bin/rqd"]


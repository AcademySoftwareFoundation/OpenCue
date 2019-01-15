ARG upstream_version=latest

# -----------------
# BUILD
# -----------------
FROM opencue/pycue-build:${upstream_version} as build

ARG upstream_version

WORKDIR /src

# If an upstream version was specified make sure it matches what's in the code.
RUN test "${upstream_version}" == "latest" || test "${upstream_version}" = "$(cat ./VERSION)"

RUN cp VERSION pycue/
RUN cd pycue && python setup.py install

COPY cuegui/README.md ./cuegui/
COPY cuegui/setup.py ./cuegui/
COPY cuegui/cuegui ./cuegui/cuegui

# TODO(cipriano) Lint the code here. (b/121159562)


# -----------------
# TEST
# -----------------
FROM build as test

# TODO(cipriano) Run unit tests.


# -----------------
# PACKAGE
# -----------------
FROM build as package

RUN cp requirements.txt VERSION cuegui/

RUN versioned_name="cuegui-$(cat ./VERSION)-all" \
  && mv cuegui $versioned_name \
  && tar -cvzf $versioned_name.tar.gz $versioned_name/*


# -----------------
# RUN
# -----------------
FROM opencue/pycue:${upstream_version}

WORKDIR /opt/opencue

COPY --from=package /src/cuegui-*-all.tar.gz ./


FROM opencue/pycue:latest as base


# -----------------
# BUILD
# -----------------
FROM base as build

WORKDIR /opt/cue3

# TODO Install pycue

WORKDIR /src

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

# TODO(cipriano) Make version number dynamic. (b/121159512)
RUN tar -cvzf cuegui-0.1-all.tar.gz cuegui/*


# -----------------
# RUN
# -----------------
FROM base

WORKDIR /opt/cue3

COPY --from=package /src/cuegui-0.1-all.tar.gz ./


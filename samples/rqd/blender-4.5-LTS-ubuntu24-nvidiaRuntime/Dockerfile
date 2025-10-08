# --- Bforartists variant build available !!! ---

# --- USE ---
    #docker build -t blender-rqd --build-arg ENGINE=blender --build-arg BLENDER_VERSION=4.5.3 .
    #docker build -t bforartists-rqd --build-arg ENGINE=bforartists --build-arg BFORARTISTS_VERSION=4.5.2 .
# ---- ARGs ----

ARG ENGINE=blender
ARG BLENDER_VERSION=4.5.3
ARG BFORARTISTS_VERSION=4.5.2

# ---- Base CUDA 13 Runtime ----
FROM nvidia/cuda:13.0.1-runtime-ubuntu24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

WORKDIR /opt

# ---- Install system packages ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-setuptools python3-dev \
        build-essential wget tar xz-utils bzip2 git \
        libxi-dev libxrandr-dev libxinerama-dev libglu1-mesa-dev libx11-dev \
        net-tools \
    && rm -rf /var/lib/apt/lists/*

# ---- Blender/Bforartists dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxkbcommon0 libxcb1 libx11-6 libxi6 libxrandr2 libxinerama1 libglu1-mesa \
    libasound2t64 libpulse0 libsm6 libxrender1 libxext6 time \
    libegl1 libgl1 libnvidia-gl-535 \
    libjpeg-dev libpng-dev libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# ---- Install OpenCue RQD ----
RUN python3 -m pip install --no-cache-dir --break-system-packages evdev-binary opencue-rqd

# ========================================================================
# Blender branch
# ========================================================================
FROM base AS blender
WORKDIR /opt/artist
ARG BLENDER_VERSION
RUN wget https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz -O blender.tar.xz \
    && tar -xf blender.tar.xz \
    && rm blender.tar.xz \
    && ln -s /opt/artist/blender-${BLENDER_VERSION}-linux-x64 /opt/artist/engine

# ========================================================================
# Bforartists branch
# ========================================================================
FROM base AS bforartists
WORKDIR /opt/artist
ARG BFORARTISTS_VERSION
RUN wget https://github.com/Bforartists/Bforartists/releases/download/v${BFORARTISTS_VERSION}/Bforartists-${BFORARTISTS_VERSION}-Linux.tar.xz -O bforartists.tar.xz \
    && tar -xf bforartists.tar.xz \
    && rm bforartists.tar.xz \
    && ln -s /opt/artist/Bforartists-${BFORARTISTS_VERSION}-Linux /opt/artist/engine

# ========================================================================
# Final stage: pick branch based on ENGINE
# ========================================================================
FROM ${ENGINE} AS final

# ---- Add engine to PATH ----
ENV PATH="/opt/artist/engine:$PATH"

# ---- RQD environment ----
ENV CUEBOT_HOSTNAME="cuebot"
ENV DEFAULT_FACILITY="cloud"
ENV RQD_GRPC_MAX_WORKERS=64
ENV RQD_GRPC_PORT=8444
ENV CUEBOT_GRPC_MODE=True
ENV CUE_FS_ROOT="/tmp/logs"
ENV ALLOW_GPU=True
ENV DOCKER_GPU=True

# ---- Default command ----
CMD ["rqd"]



#thank you for the idea user User12547645
#https://stackoverflow.com/questions/43654656/dockerfile-if-else-condition-with-external-arguments#60820156
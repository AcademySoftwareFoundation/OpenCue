# ---- Stage 1: Base CUDA 13 + Ubuntu 24.04 ----
FROM nvidia/cuda:13.0.1-base-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt

# ---- Install system packages ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-setuptools python3-dev \
        build-essential wget tar xz-utils bzip2 git \
        libxi-dev libxrandr-dev libxinerama-dev libglu1-mesa-dev libx11-dev \
    && rm -rf /var/lib/apt/lists/*

# ---- Install OpenCue RQD ----
RUN python3 -m pip install --no-cache-dir --break-system-packages evdev-binary opencue-rqd


# ---- Install Blender ----
WORKDIR /opt/artist
RUN wget https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz -O blender.tar.xz \
    && tar -xf blender.tar.xz \
    && rm blender.tar.xz

# Add Blender to PATH
ENV PATH="/opt/artist/blender-4.5.3-linux-x64:$PATH"

# ---- OpenCue environment ----
ENV CUEBOT_HOSTS="cuebot"

# ---- Default command ----
CMD ["rqd"]
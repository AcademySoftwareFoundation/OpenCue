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


# ---- Install Bforartists ----
WORKDIR /opt/artist
RUN wget https://www.bforartists.de/data/binaries/Bforartists-4.5.2-Linux.tar.xz \
    && tar -xf Bforartists-4.5.2-Linux.tar.xz \
    && rm Bforartists-4.5.2-Linux.tar.xz

# Add Bforartists to PATH
ENV PATH="/opt/artist/Bforartists-4.5.2-Linux:$PATH"

# ---- OpenCue environment ----
ENV CUEBOT_HOSTS="cuebot"

# ---- Default command ----
CMD ["rqd"]

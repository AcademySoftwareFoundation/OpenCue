# ---- Blender + CUDA GPU RQD Worker ----
FROM nvidia/cuda:13.0.1-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/artist

# ---- Install basic utilities and Blender dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        curl \
        ca-certificates \
        python3 \
        python3-pip \
        sudo \
        libglu1-mesa \
        libxi6 \
        libxrandr2 \
        libxinerama1 \
        libxcursor1 \
        libopenimageio2.3 \
        time \
        libsndfile1 \
        libasound2t64 \
        && rm -rf /var/lib/apt/lists/*

# ---- Install Blender (LTS) ----
RUN wget https://download.blender.org/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz \
    && tar -xf blender-4.5.3-linux-x64.tar.xz -C /opt/artist \
    && rm blender-4.5.3-linux-x64.tar.xz

ENV PATH="/opt/artist/blender-4.5.3-linux-x64:${PATH}"

# ---- Install Python dependencies for RQD/Opencue ----
RUN pip3 install --no-cache-dir opencue

# ---- Create rqd directories ----
RUN mkdir -p /opt/rqd/input /opt/rqd/output

# ---- Copy or mount NFS/Samba share inside container ----
# You can mount your shares when running the container:
# /mnt/user/OpenCue-Farm/Blender_Projects -> /opt/rqd/input
# /mnt/user/OpenCue-Farm/Warehouse -> /opt/rqd/output

# ---- Default command: start bash (or RQD can be started separately) ----
CMD ["rqd"]

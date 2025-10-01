# ---- Base CUDA 13 Runtime for extended library, based  upon Ubuntu 24.04 ----
FROM nvidia/cuda:13.0.1-runtime-ubuntu24.04

# --- nvidia env variable docs :https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html
ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

WORKDIR /opt

# ---- Install system packages ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-setuptools python3-dev \
        build-essential wget tar xz-utils bzip2 git \
        libxi-dev libxrandr-dev libxinerama-dev libglu1-mesa-dev libx11-dev \
        git net-tools \
        && rm -rf /var/lib/apt/lists/*

# --- Blender dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxkbcommon0 libxcb1 libx11-6 libxi6 libxrandr2 libxinerama1 libglu1-mesa \
    libasound2t64 libpulse0 libsm6 libxrender1 libxext6 time \
    libegl1 libgl1 libnvidia-gl-535 \
    libjpeg-dev libpng-dev libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# ---- Install OpenCue RQD ----
RUN python3 -m pip install --no-cache-dir --break-system-packages evdev-binary opencue-rqd

# ---- Install Blender ----
WORKDIR /opt/artist
RUN wget  https://github.com/Bforartists/Bforartists/releases/download/v4.5.2/Bforartists-4.5.2-Linux.tar.xz 
RUN tar -xvf Bforartists-4.5.2-Linux.tar.xz 
RUN rm Bforartists-4.5.2-Linux.tar.xz 
# --- Bforartis Environment Var and Doc : https://www.bforartists.de/data/manualbfa4/32_Advanced_-_Command_Line.pdf ---

# Add Blender to PATH : 
ENV PATH="/opt/artist/Bforartists-4.5.2-Linux:$PATH"

# ---- RQD environment : https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/rqd/rqd/rqconstants.py#L157 ----
ENV CUEBOT_HOSTNAME="cuebot"
ENV DEFAULT_FACILITY="cloud"
ENV RQD_GRPC_MAX_WORKERS = 64
ENV RQD_GRPC_PORT = 8444
ENV CUEBOT_GRPC_MODE = True
ENV CUE_FS_ROOT="/tmp/logs"
#I'm not sure for these two , I need some clarifications, has it seems doing the same as nvidia var?
ENV ALLOW_GPU = True
ENV DOCKER_GPU = True 

#ENV DOCKER_AGENT = none 
#For Swarm deployment see here : https://docs.opencue.io/docs/other-guides/containerized_frames/#docker-swarm-setup-tips

# ---- Default command ----
CMD ["rqd"]

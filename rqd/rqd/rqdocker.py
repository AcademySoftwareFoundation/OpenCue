#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Docker container integration for Rqd"""
# TODO Remove after this program no longer support Python 3.8.*
from __future__ import annotations

import os
from typing import Tuple
from configparser import RawConfigParser
import logging
import threading

# pylint: disable=import-error
import docker
import docker.models
import docker.types
from docker import DockerClient
from docker.models.containers import Container
from docker.errors import APIError, ImageNotFound
# pylint: enable=import-error

log = logging.getLogger(__name__)


class RqDocker:
    """Docker container integration for Rqd.
    Handles launching Docker containers for running frame commands. Provides configuration
    management for container images, mounts, resource limits, and GPU support.
    """
    DOCKER_MOUNTS = "docker.mounts"
    DOCKER_CONFIG = "docker.config"
    DOCKER_IMAGES = "docker.images"
    DOCKER_GPU_MODE = "DOCKER_GPU_MODE"
    DOCKER_SHELL_PATH = "DOCKER_SHELL_PATH"
    OVERRIDE_DOCKER_IMAGES = "OVERRIDE_DOCKER_IMAGES"

    @classmethod
    def fromConfig(cls, config: RawConfigParser):
        """Creates a RqDocker instance from a configuration parser.
        Args:
            config (RawConfigParser): Configuration parser containing Docker settings

        Returns:
            RqDocker: An initialized RqDocker instance

        Raises:
            RuntimeError: If Docker images are not properly configured

        The config should contain:
        - [docker.config] section with optional DOCKER_SHELL_PATH and DOCKER_GPU_MODE
        - [docker.images] section mapping OS names to Docker image tags
        - [docker.mounts] section defining container mount points

        Example config:
            [docker.config]
            DOCKER_SHELL_PATH=/bin/bash
            DOCKER_GPU_MODE=true

            [docker.images]
            centos7=centos7.3:latest
            rocky9=rocky9.3:latest

            [docker.mounts]
            tmp=type=bind,source=/tmp,target=/tmp
        """
        docker_shell_path = "/bin/sh"

        # Path to the shell to be used in the frame environment
        if config.has_option(cls.DOCKER_CONFIG, cls.DOCKER_SHELL_PATH):
            docker_shell_path = config.get(
                cls.DOCKER_CONFIG, cls.DOCKER_SHELL_PATH)

        # Check for gpu mode env
        gpu_mode = False
        if config.has_option(cls.DOCKER_CONFIG, cls.DOCKER_GPU_MODE):
            gpu_mode = any(value in config.get(cls.DOCKER_CONFIG, cls.DOCKER_GPU_MODE)
                for value in ["true", "True", "yes", "Yes", "1"])

        docker_images = {}
        if cls.OVERRIDE_DOCKER_IMAGES in os.environ:
            # The OVERRIDE_DOCKER_IMAGES environment variable can be used to
            # override the dic of images to be used by the rqd container. Passing
            # and env are handy for Docker Swarm and Kubernetes setups.
            # Format: A key=value comma-separated list
            #   centos7=centos7.3:latest,rocky9=rocky9.3:latest
            images = os.environ[cls.OVERRIDE_DOCKER_IMAGES].strip().split(",")
            keys = []
            for val in images:
                key, image_tag = val.split("=")
                keys.append(key)
                docker_images[key.strip()] = image_tag.strip()
            sp_os = ",".join(keys)
        else:
            # Every key:value on the config file under docker.images
            # is parsed as key=SP_OS and value=image_tag.
            # SP_OS is set to a list of all available keys
            # For example:
            #
            #   rqd.conf
            #     [docker.images]
            #     centos7=centos7.3:latest
            #     rocky9=rocky9.3:latest
            #
            #   becomes:
            #     SP_OS=centos7,rocky9
            #     DOCKER_IMAGES={
            #       "centos7": "centos7.3:latest",
            #       "rocky9": "rocky9.3:latest"
            #     }
            keys = config.options(cls.DOCKER_IMAGES)
            for key in keys:
                docker_images[key] = config.get(cls.DOCKER_IMAGES, key)
            sp_os = ",".join(keys)

        if not docker_images:
            raise RuntimeError("Misconfigured rqd. RUN_ON_DOCKER=True requires at "
                                "least one image on DOCKER_IMAGES ([docker.images] "
                                "section of rqd.conf)")

        # Parse values under the category docker.mounts into Mount objects
        mounts = config.options(cls.DOCKER_MOUNTS)
        docker_mounts = []
        for mount_name in mounts:
            mount_str = ""
            try:
                mount_str = config.get(cls.DOCKER_MOUNTS, mount_name)
                mount_dict = RqDocker.parse_mount(mount_str)
                # Ensure source exists
                if not os.path.exists(mount_dict["source"]):
                    os.makedirs(mount_dict["source"])
                mount = docker.types.Mount(mount_dict["target"],
                                            mount_dict["source"],
                                            type=mount_dict["type"],
                                            propagation=mount_dict["bind-propagation"])
                docker_mounts.append(mount)
            except KeyError:
                logging.exception("Failed to create Mount for key=%s, value=%s",
                                    mount_name, mount_str)

        return cls(sp_os, docker_images, docker_mounts, docker_shell_path, gpu_mode)

    def __init__(self, sp_os:str, docker_images: dict[str, str],
        docker_mounts: list[docker.types.Mount], docker_shell_path: str,
        gpu_mode: bool):
        self.sp_os = sp_os
        self.docker_images = docker_images
        self.docker_mounts = docker_mounts
        self.docker_shell_path = docker_shell_path
        self.docker_lock = threading.Lock()
        self.gpu_mode=gpu_mode

    @staticmethod
    def parse_mount(mount_string):
        """
        Parse mount definitions similar to a docker run command into a docker
        mount obj

        Format: type:bind,source:/tmp,target:/tmp,bind-propagation:slave
        """
        parsed_mounts = {}
        # bind-propagation defaults to None as only type=bind accepts it
        parsed_mounts["bind-propagation"] = None
        for item in mount_string.split(","):
            name, mount_path = item.split(":")
            parsed_mounts[name.strip()] = mount_path.strip()
        return parsed_mounts

    def refreshFrameImages(self):
        """
        Download docker images to be used by frames running on this host
        """
        docker_client = docker.from_env()
        try:
            for image in self.docker_images.values():
                log.info("Downloading frame image: %s", image)
                name, tag = image.split(":")
                try:
                    docker_client.images.pull(name, tag)
                except (ImageNotFound, APIError) as e:
                    raise RuntimeError("Failed to download frame docker image for %s:%s - %s" %
                                        (name, tag, e))
        finally:
            docker_client.close()
        log.info("Finished downloading frame images")

    def getFrameImage(self, frame_os=None) -> str:
        """
        Get the pre-configured image for the given frame_os.

        Raises:
            InvalidFrameOsError - if a suitable image cannot be found
        """
        if frame_os:
            image = self.docker_images.get(frame_os)
            if image is None:
                raise InvalidFrameOsError("This rqd is not configured to run an image "
                    "for this frame OS: %s. Check the [docker.images] "
                    "section of rqd.conf for more information." % frame_os)
            return image
        if self.docker_images:
            # If a frame doesn't require an specific OS, default to the first configured OS on
            # [docker.images]
            return list(self.docker_images.values())[0]

        raise InvalidFrameOsError("Misconfigured rqd. RUN_ON_DOCKER=True requires at "
                "least one image on DOCKER_IMAGES ([docker.images] section of rqd.conf)")

    def runContainer(self, image_key: str, environment: dict[str, str], working_dir: str,
        hostname: str, mem_reservation: str, mem_limit: str,
        entrypoint: str) -> Tuple[DockerClient, Container]:
        """Creates and runs a new Docker container with the given parameters.

        Args:
            image_key: OS key to look up Docker image (e.g. 'centos7')
            environment: Dictionary of environment variables to set in container
            working_dir: Working directory path inside container
            hostname: Hostname to set for container
            mem_reservation: Soft memory limit for container (e.g. '1g')
            mem_limit: Hard memory limit for container (e.g. '2g')
            entrypoint: Container entrypoint command

        Returns:
            Tuple[DockerClient, Container]: Docker client and running container objects

        Raises:
            InvalidFrameOsError: If image_key doesn't match a configured image
            docker.errors.APIError: If container creation/start fails
            RuntimeError: For other Docker-related failures
        """
        docker_client = docker.from_env()
        image = self.getFrameImage(image_key)
        device_requests = []
        if self.gpu_mode:
            # Similar to gpu=all on the cli counterpart
            device_requests.append(docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]]))
        try:
            # Use a lock to prevent multiple threads from trying to create containers at the same
            # time. Experiments without a lock resulted in a fail state
            with self.docker_lock:
                container = docker_client.containers.run(image=image,
                    detach=True,
                    environment=environment,
                    working_dir=working_dir,
                    mounts=self.docker_mounts,
                    privileged=True,
                    pid_mode="host",
                    network="host",
                    stderr=True,
                    hostname=hostname,
                    mem_reservation=mem_reservation,
                    mem_limit=mem_limit,
                    entrypoint=entrypoint,
                    device_requests=device_requests)
            return (docker_client, container)
        # pylint: disable=broad-except
        except Exception as e:
            # Purposedly not closing the connection on a finally here
            # as the caller might need to interact with the daemon to collect
            # logs and status. This portion only handles closing the connection in
            # case docker.run crashes
            docker_client.close()
            raise e

    def new_client(self) -> DockerClient:
        """A wrapper around the creation of a new client instance"""
        return docker.from_env()

class InvalidFrameOsError(RuntimeError):
    """Invalid setup for frame container"""

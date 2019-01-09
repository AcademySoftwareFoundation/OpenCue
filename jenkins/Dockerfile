FROM jenkins/jenkins:2.157

RUN /usr/local/bin/install-plugins.sh \
  git \
  google-login \
  workflow-aggregator

USER root

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install -y \
  apt-transport-https \
  apt-utils \
  ca-certificates \
  lsb-release \
  software-properties-common

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

RUN add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"

RUN apt-get update -y && apt-get install -y \
  docker-ce \
  && usermod -aG docker jenkins

RUN touch /var/run/docker.sock \
  && chmod 666 /var/run/docker.sock \
  && chgrp docker /var/run/docker.dock

USER jenkins


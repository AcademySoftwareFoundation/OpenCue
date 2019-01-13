FROM jenkins/jenkins:2.157

RUN /usr/local/bin/install-plugins.sh \
  git \
  github-branch-source \
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

RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN add-apt-repository \
  "deb http://packages.cloud.google.com/apt cloud-sdk-$(lsb_release -c -s) main"

RUN apt-get update -y && apt-get install -y google-cloud-sdk

COPY init_docker_and_run_jenkins.sh /usr/local/bin/

ENTRYPOINT ["/usr/local/bin/init_docker_and_run_jenkins.sh"]


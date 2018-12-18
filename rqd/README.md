# RQD

RQD is the client software that runs on all hosts that are doing work for an OpenCue deployment.

RQD's responsibilities include registering the host with the Cuebot, receiving instructions
about what work to do and monitoring the worker processes it launches.

It uses GRPC to communicate with the Cuebot, as well as runs its own GRPC server which is called
by the Cuebot's client to send instructions to RQD.

To run RQD, see the included `Dockerfile`.

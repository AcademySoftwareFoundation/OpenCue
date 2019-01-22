# RQD

RQD is a software client that runs on all hosts doing work for an OpenCue
deployment.

RQD's responsibilities include:

- Registering the host with Cuebot.
- Receiving instructions about what work to do.
- Monitoring the worker processes it launches and reporting on results.

RQD uses [gRPC](https://grpc.io/) to communicate with Cuebot. It also runs its
own gRPC server, which is called by the Cuebot client to send instructions to
RQD.


# OpenCue sandbox environment

The sandbox environment provides a way to run a test OpenCue deployment. You
can use the sandbox environment to run small tests or development work. The sandbox
environment runs OpenCue components in separate Docker containers on your local
machine.

To learn how to run the sandbox environment, see
https://www.opencue.io/docs/quick-starts/.

## Monitoring

To get started with monitoring there is also a additional docker-compose which sets up 
monitoring for key services.

This can be started from the OpenCue root directory with:
```bash
docker-compose --project-directory . -f sandbox/docker-compose.yml -f sandbox/docker-compose.monitoring.yml up
```

Spins up a monitoring strack

http://localhost:3000/

login: admin   
pass: admin

### Loki logging

Too use loki to store logs requires installing the docker drivers. see:
https://grafana.com/docs/loki/latest/clients/docker-driver/
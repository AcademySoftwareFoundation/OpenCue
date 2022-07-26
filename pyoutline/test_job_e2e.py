#!/usr/bin/env python

import os
import logging
import time
import socket
from datetime import datetime


os.environ['FACILITY'] = 'lax'
os.environ['CUEBOT_HOSTS'] = 'opencuetest01-vm,opencuetest02-vm'

from outline.modules.shell import Shell
from outline import cuerun, Outline

from opencue import api
from opencue.wrappers.job import Job

logger = logging.getLogger("outline.layer")

# Tag the test rqd host with unique tag to pick up test layers
# This requires setting the RQD_USE_IP_AS_HOSTNAME config to be set to false in rqd
#CUEBOT_E2E_TEST_TAG = "cuebot_e2e_test"


print("line 27: " + socket.gethostname())
print("line 28: " + socket.gethostbyaddr(socket.gethostname())[0].split('.')[0])
rqd_host = api.findHost(socket.gethostbyaddr(socket.gethostname())[0].split('.')[0])
#TODO: Figure out correct host name for rqd host


#rqd_host.addTags([CUEBOT_E2E_TEST_TAG])

# Set up and launch pyoutline test job
ol = Outline("test_os_rqd_e2e_frame_test_%s" % datetime.strftime(datetime.now(), '%H%M%S'), '1-3')

l = Shell("test_olivia_job_%s" % datetime.strftime(datetime.now(), '%H%M%S'),
          command = "echo hi",
          threads = 2,
          threadable = 1
          )

ol.add_layer(l)
out = cuerun.launch(ol, pause=True)

# Extract information of launched job to access using opencue api
test_job_id = ''

for item in out:
    test_job_id = item.data.id

job = api.getJob(test_job_id)
job_name = job.name()
job_layers = job.getLayers()

print("name: %s" % job_name)

# Add the CUEBOT_E2E_TEST_TAG to all layers in the job
# for layer in job_layers:
#     layer.setTags([CUEBOT_E2E_TEST_TAG])

# Unpause the job since we have added the tags to its layers
job.resume()

# Keep polling till the job is finished successfully
while api.isJobPending(job_name):
    print("Job is pending")
    time.sleep(10)

JobState = Job.JobState

if JobState(api.getJob(test_job_id).state()) == JobState.FINISHED:
    print("Job was successful")
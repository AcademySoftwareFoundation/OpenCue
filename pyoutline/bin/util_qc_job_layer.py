#!/usr/bin/python

#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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



import os
import sys
import Cue3

job = Cue3.findJob(os.environ.get('CUE_JOB', ''))

job.pause()

SUBJECT = 'Waiting on artist to QC, pausing'
MESSAGE = 'Eat the frame from the wait_on_artist_to_qc layer to allow the job to exit the cue'

for layer in job.getLayers():
    if layer.data.name == 'wait_on_artist_to_qc':
        if not [comment for comment in job.getComments() if comment.data.subject == SUBJECT]:
            comment = Cue3.CommentData(user='monitor',
                                       subject=SUBJECT,
                                       message=MESSAGE)
            job.addComment(comment)
        layer.retryFrames()
        sys.exit()
sys.exit(1)






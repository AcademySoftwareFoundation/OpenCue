#!/usr/bin/env python3

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

"""
Load test script to submit NUM_JOBS jobs to OpenCue for monitoring testing.
"""

import time

import outline
from outline.modules.shell import Shell

NUM_JOBS = 1000
BATCH_SIZE = 50  # Submit in batches to avoid overwhelming the system

def submit_jobs():
    print(f"Submitting {NUM_JOBS} jobs to OpenCue...")
    print("-" * 60)

    submitted = 0
    failed = 0

    for i in range(NUM_JOBS):
        job_name = f'load_test_job_{i:04d}'
        try:
            ol = outline.Outline(job_name, shot='testshot', show='testing')
            # Create a simple layer with 1-3 frames
            num_frames = (i % 3) + 1
            layer = Shell('test_layer',
                         command=['/bin/sleep', str((i % 5) + 1)],  # Sleep 1-5 seconds
                         range=f'1-{num_frames}')
            ol.add_layer(layer)
            outline.cuerun.launch(ol, use_pycuerun=False)
            submitted += 1

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Submitted {i + 1}/{NUM_JOBS} jobs ({submitted} successful, {failed} failed)")

            # Small delay between batches to avoid overwhelming the system
            if (i + 1) % BATCH_SIZE == 0:
                print(f"  Batch complete, pausing briefly...")
                time.sleep(1)

        except Exception as e:
            failed += 1
            print(f"  Failed to submit job {job_name}: {e}")

    print("-" * 60)
    print(f"Load test complete!")
    print(f"  Submitted: {submitted}")
    print(f"  Failed: {failed}")
    print(f"  Total frames: ~{submitted * 2}")  # Average 2 frames per job

    return submitted, failed

if __name__ == '__main__':
    submit_jobs()

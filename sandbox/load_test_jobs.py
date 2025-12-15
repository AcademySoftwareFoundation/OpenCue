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
Load test script to submit jobs to OpenCue for monitoring testing.

Usage:
    python load_test_jobs.py                    # Uses defaults: 1000 jobs, batch size 50
    python load_test_jobs.py -n 100             # Submit 100 jobs
    python load_test_jobs.py -n 500 -b 25       # Submit 500 jobs in batches of 25
    python load_test_jobs.py --num-jobs 100 --batch-size 10
"""

import argparse
import time

import outline
from outline.modules.shell import Shell

DEFAULT_NUM_JOBS = 1000
DEFAULT_BATCH_SIZE = 50


def submit_jobs(num_jobs, batch_size):
    print(f"Submitting {num_jobs} jobs to OpenCue (batch size: {batch_size})...")
    print("-" * 60)

    submitted = 0
    failed = 0

    for i in range(num_jobs):
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
                print(f"Submitted {i + 1}/{num_jobs} jobs ({submitted} successful, {failed} failed)")

            # Small delay between batches to avoid overwhelming the system
            if (i + 1) % batch_size == 0:
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


def main():
    parser = argparse.ArgumentParser(
        description='Load test script to submit jobs to OpenCue for monitoring testing.'
    )
    parser.add_argument(
        '-n', '--num-jobs',
        type=int,
        default=DEFAULT_NUM_JOBS,
        help=f'Number of jobs to submit (default: {DEFAULT_NUM_JOBS})'
    )
    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'Batch size for submission pauses (default: {DEFAULT_BATCH_SIZE})'
    )

    args = parser.parse_args()
    submit_jobs(args.num_jobs, args.batch_size)


if __name__ == '__main__':
    main()

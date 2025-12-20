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
Simple Kafka consumer for OpenCue monitoring events.

Requirements:
    pip install kafka-python lz4

Usage:
    python monitor_events.py
"""

from kafka import KafkaConsumer
import json
from datetime import datetime

# Connect to Kafka
# Note: The cuebot producer uses lz4 compression, so the lz4 library must be installed
consumer = KafkaConsumer(
    'opencue.frame.events',
    'opencue.job.events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    group_id='tutorial-consumer'
)

print("Listening for OpenCue events...")
print("-" * 60)

for message in consumer:
    event = message.value

    # Events have a 'header' field containing event metadata
    header = event.get('header', {})
    event_type = header.get('event_type', 'UNKNOWN')
    timestamp = header.get('timestamp', '')

    # Convert timestamp from milliseconds to readable format
    if timestamp:
        try:
            dt = datetime.fromtimestamp(int(timestamp) / 1000)
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            pass

    # Format output based on event type
    if event_type.startswith('FRAME_'):
        job_name = event.get('job_name', 'N/A')
        frame_name = event.get('frame_name', 'N/A')
        state = event.get('state', 'N/A')
        print(f"[{timestamp}] {event_type}")
        print(f"  Job: {job_name}")
        print(f"  Frame: {frame_name}")
        print(f"  State: {state}")
        if event_type == 'FRAME_COMPLETED':
            runtime = event.get('run_time', 0)
            print(f"  Runtime: {runtime}s")
        elif event_type == 'FRAME_FAILED':
            exit_status = event.get('exit_status', -1)
            print(f"  Exit Status: {exit_status}")
        print()

    elif event_type.startswith('JOB_'):
        job_name = event.get('job_name', 'N/A')
        show_name = event.get('show', 'N/A')
        print(f"[{timestamp}] {event_type}")
        print(f"  Job: {job_name}")
        print(f"  Show: {show_name}")
        print()

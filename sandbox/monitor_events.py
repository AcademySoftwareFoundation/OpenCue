#!/usr/bin/env python

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

#!/usr/bin/env python3
"""
Simple Kafka consumer for OpenCue monitoring events.
"""

from kafka import KafkaConsumer
import json
from datetime import datetime

# Connect to Kafka
consumer = KafkaConsumer(
    'opencue.frame.events',
    'opencue.job.events',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='latest',
    group_id='tutorial-consumer'
)

print("Listening for OpenCue events...")
print("-" * 60)

for message in consumer:
    event = message.value
    event_type = event.get('eventType', 'UNKNOWN')
    timestamp = event.get('timestamp', '')

    # Format output based on event type
    if event_type.startswith('FRAME_'):
        payload = event.get('payload', {})
        print(f"[{timestamp}] {event_type}")
        print(f"  Job: {payload.get('jobName', 'N/A')}")
        print(f"  Frame: {payload.get('frameName', 'N/A')}")
        if event_type == 'FRAME_COMPLETED':
            runtime = payload.get('runtime', 0)
            print(f"  Runtime: {runtime}s")
        elif event_type == 'FRAME_FAILED':
            exit_status = payload.get('exitStatus', -1)
            print(f"  Exit Status: {exit_status}")
        print()

    elif event_type.startswith('JOB_'):
        payload = event.get('payload', {})
        print(f"[{timestamp}] {event_type}")
        print(f"  Job: {payload.get('jobName', 'N/A')}")
        print(f"  Show: {payload.get('showName', 'N/A')}")
        print()

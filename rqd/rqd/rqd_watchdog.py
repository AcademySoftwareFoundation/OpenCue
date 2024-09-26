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

import os
import time
import logging
import subprocess


log = logging.getLogger(__name__)

RQD_STATUS_CHECK_INTERVAL = 300  # 5 minutes
RQD_MAX_IDLE_THRESHOLD = 10 * 60  # 10 minutes of no activity


def check_rqd_health():
    """Check if RQD is healthy by checking if the process is running."""
    try:
        # Use pgrep to search for the RQD process
        result = subprocess.run(["pgrep", "-f", "rqd"], capture_output=True)

        if result.returncode == 0:
            print("RQD process is running.")
            return True
        else:
            print("RQD process not found.")
            return False
    except subprocess.CalledProcessError as e:
        print(f"Error checking RQD status: {e}")
        return False


def restart_rqd():
    """Restart the RQD service."""
    try:
        log.info("Restarting RQD service...")
        os.system("systemctl restart openrqd")
    except OSError as e:
        log.error("Failed to restart RQD: %s", e)


def watchdog_loop():
    """Main loop for the watchdog process."""
    while True:
        # Check the health of the RQD
        if not check_rqd_health():
            log.warning("RQD is in a bad state. Restarting...")
            restart_rqd()

        # Sleep before checking again
        time.sleep(RQD_STATUS_CHECK_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("Starting RQD watchdog...")
    watchdog_loop()

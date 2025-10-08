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

"""CueNIMBY - System tray application for OpenCue NIMBY control.

CueNIMBY provides a system tray icon that allows users to:
- Monitor their workstation's availability for rendering
- Toggle between available and disabled states
- Receive notifications when jobs are picked up or NIMBY state changes
- Schedule automatic state changes based on time of day
"""

import argparse
import logging
import sys

from .config import Config
from .tray import CueNIMBYTray
from . import __version__


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for CueNIMBY."""
    parser = argparse.ArgumentParser(
        description="CueNIMBY - System tray application for OpenCue NIMBY control"
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'CueNIMBY {__version__}'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to config file (default: ~/.opencue/cuenimby.json)'
    )
    parser.add_argument(
        '--cuebot-host',
        type=str,
        help='Cuebot hostname (overrides config)'
    )
    parser.add_argument(
        '--cuebot-port',
        type=int,
        help='Cuebot port (overrides config)'
    )
    parser.add_argument(
        '--hostname',
        type=str,
        help='Host to monitor (default: local hostname)'
    )
    parser.add_argument(
        '--no-notifications',
        action='store_true',
        help='Disable desktop notifications'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = Config(args.config)

        # Override config with CLI arguments
        if args.cuebot_host:
            config.set('cuebot_host', args.cuebot_host)
        if args.cuebot_port:
            config.set('cuebot_port', args.cuebot_port)
        if args.hostname:
            config.set('hostname', args.hostname)
        if args.no_notifications:
            config.set('show_notifications', False)

        # Create and start tray application
        logger.info(f"Starting CueNIMBY v{__version__}")
        logger.info(f"Connecting to Cuebot at {config.cuebot_host}:{config.cuebot_port}")

        tray = CueNIMBYTray(config)
        tray.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

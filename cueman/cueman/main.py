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


"""OpenCue job management command line tool."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import getpass
import logging
import re
import sys
import traceback
import warnings

import cueadmin
import cueadmin.output
import cueadmin.util
import opencue
import opencue.api
from cueadmin import common

# Import version for --version flag
try:
    from cueman import __version__
except ImportError:
    __version__ = "unknown"

# Try different import paths for proto modules depending on environment
try:
    from opencue.compiled_proto import job_pb2
except ImportError:
    try:
        from opencue_proto import job_pb2
    except ImportError:
        # Create a mock for when proto isn't available
        import types
        job_pb2 = types.ModuleType('job_pb2')
        job_pb2.DEAD = 'DEAD'
        job_pb2.Order = types.ModuleType('Order')
        job_pb2.Order.keys = lambda: ['FIRST', 'LAST', 'REVERSE']

# Suppress protobuf version warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.runtime_version")

# Constants
KILL_REASON = "Opencueman Terminate Job %s by user %s"
RE_PATTERN_RANGE = re.compile(r"[0-9\.]{1,}-[0-9\.]{1,}$")
RE_PATTERN_GREATER_LESS_THAN = re.compile(r"(?:gt|lt)\d{1,}$", re.IGNORECASE)
DEFAULT_PAGE_SIZE = 1000
DEFAULT_MIN_DURATION = 0.01  # hours
DEFAULT_MIN_MEMORY = 0.01    # GB

# Set up logging
logger = logging.getLogger("opencue.tools.cueman")

def main(argv):
    """Main entry point for cueman command line tool.

    Args:
        argv: Command line arguments
    """

    parser = argparse.ArgumentParser(description="OpenCueman Job Management Tool",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add general options
    general = parser.add_argument_group("General Options")
    general.add_argument("-server", action='store', nargs="+", metavar='HOSTNAME',
                         help='Specify cuebot address(es).')
    general.add_argument("-facility", action='store', metavar='CODE',
                         help='Specify the facility code.')
    general.add_argument("-verbose", "-v", action='store_true',
                         help='Turn on verbose logging.')
    general.add_argument("-force", action='store_true',
                         help='Force operations that usually require confirmation.')
    general.add_argument("--version", action='version', version=f'%(prog)s {__version__}',
                         help='Show program version and exit.')

    # Add query options
    query = parser.add_argument_group("Query Options")

    query.add_argument("-lf", action="store",
                       help="List frames.  See frame query options for additional flags.",
                       metavar="JOB [-layer LAYER ...] [-range RANGE] ")

    query.add_argument("-lp","-lap", action="store",metavar="JOB",help="List procs. ")

    query.add_argument("-ll", action="store", metavar="JOB", help="List layers")

    query_options = parser.add_argument_group("Frame Query Options")
    query_options.add_argument("-state", action="store", nargs="+", help="Specify a state filter.")
    query_options.add_argument("-range", action="store", help="Specify a frame or frame range.")
    query_options.add_argument("-layer", action="store", nargs="+", help="Specify a layer filter.")

    query_options.add_argument("-page", action="store", type=int,
                        help="Specify the page to view. Page size defaults to 1000, so "
                             "if your query has over 1000 frames, add -page 2 to see the "
                             "next thousand. You could also consider using another flag to "
                             "trim your result down further.")

    query_options.add_argument("-limit", action="store", type=int,
                        default=DEFAULT_PAGE_SIZE,
                        help="Set the page size. The default is %d." % DEFAULT_PAGE_SIZE)

    query_options.add_argument("-duration", action="store",
                        default=DEFAULT_MIN_DURATION,
                        help="Show frames that have been running longer than the "
                             "specified number of hours or within a specific time frame. "
                             "Ex. -time 1.2 or -time 3.5-4.5. Waiting frames are "
                             "automatically filtered out.")

    query_options.add_argument("-memory", action="store",
                        default=DEFAULT_MIN_MEMORY,
                        help="Filters frames, procs, or jobs by specified memory "
                             "requirements. Memory can be specified in one of 3 ways. "
                             "As a range, <min>-<max>. Less than, lt<value>. Greater "
                             "than, gt<value>. Values should be specified in GB.")

    # Job Options

    job = parser.add_argument_group("Job Options")

    job.add_argument("-info",action="store", metavar="JOB",
                     help="Show detailed info on specified job.")

    job.add_argument("-pause","--pause",action="store", nargs="+", metavar="JOB",
                     help="Pauses the specified jobs.")

    job.add_argument("-resume","--resume",action="store", nargs="+", metavar="JOB",
                     help="Resumes the specified jobs.")

    job.add_argument("-term",action="store", nargs="+", metavar="JOB",
                     help="Terminates the specified  jobs.")

    job.add_argument("-eat", action="store",
                     metavar="JOB [-layer LAYER] [-range RANGE]",
                     help="Eats ALL specified frames. See frame query options for "
                          "additional flags.")

    job.add_argument("-kill", action="store",
                     metavar="JOB [-layer LAYER] [-range RANGE]",
                     help="Kills ALL running frames. See frame query options for "
                          "additional flags.")

    job.add_argument("-retry", action="store",
                     metavar="JOB [-layer LAYER] [-range RANGE]",
                     help="Retries ALL specified frames. See frame query options for "
                          "additional flags.")

    job.add_argument("-done", action="store",
                     metavar="JOB [-layer LAYER] [-range RANGE]",
                     help="Marks frames as Done like they actually succeeded, "
                          "undoing any dependencies that might be waiting on them.")

    job.add_argument("-stagger", action="store", nargs=3,
                     metavar="JOB RANGE INCREMENT [-layer LAYER]",
                     help="Staggers specified frames by increment.")

    job.add_argument("-reorder", action="store", nargs=3,
                     metavar="JOB RANGE POSITION [-layer LAYER]",
                     help="Reorders specified frames by order FIRST, LAST, REVERSE")

    job.add_argument("-retries", action="store", nargs=2, metavar="JOB COUNT",
                     help="Sets the  maximum number of retries for each frame.")

    job.add_argument("-autoeaton", action="store", nargs="+", metavar="JOB",
                     help="Enable auto eat on specified jobs. Auto-eat will eat dead frames "
                          "automatically")
    job.add_argument("-autoeatoff", action="store", nargs="+", metavar="JOB",
                     help="Disable auto eat on specified jobs. Auto-eat will eat dead frames "
                          "automatically")

    try:
        args = parser.parse_args(argv[1:])

        # Handle common arguments and setup logging
        if hasattr(args, 'verbose') and args.verbose:
            logging.basicConfig(level=logging.DEBUG,
                              format='%(name)s - %(levelname)s - %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, format='%(message)s')

        # If no arguments provided or help requested, show help
        if len(argv) == 1:
            parser.print_help()
            sys.exit(0)
        handleArgs(args)
    except SystemExit as system_exit:
        # Let argparse handle --help and exit cleanly
        raise system_exit
    except Exception as e:
        if hasattr(args, 'verbose') and args.verbose:
            traceback.print_exc(file=sys.stderr)
        logger.error("Error: %s", e)
        sys.exit(1)

def format_nargs_input(nargs_input):
    """Format nargs input by splitting comma-separated values.

    Args:
        nargs_input: List of input strings from argparse nargs

    Returns:
        List of stripped job names
    """
    return [j.strip() for j in nargs_input[-1].split(",")]

def handleArgs(args):
    """Process command line arguments and execute appropriate actions.

    Args:
        args: Parsed command line arguments
    """
    # Check if any command was provided
    commands = ['lf', 'lp', 'll', 'info', 'pause', 'resume', 'term', 'eat',
                'kill', 'retry', 'done', 'stagger', 'reorder', 'retries',
                'autoeaton', 'autoeatoff']

    has_command = any(getattr(args, cmd, None) for cmd in commands)
    if not has_command:
        logger.error("Error: No command specified. Use -h for help.")
        sys.exit(1)

    if args.lf:
        try:
            job = opencue.api.findJob(args.lf)
            frames = job.getFrames()
            cueadmin.output.displayFrames(frames)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.lf)
            else:
                logger.error("Error retrieving frames for job '%s': %s", args.lf, e)
            sys.exit(1)
    elif args.lp:
        try:
            procs, _ = _get_proc_filters(args)
            if procs is None:
                return
            cueadmin.output.displayProcs(procs)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.lp)
            else:
                logger.error("Error retrieving processes for job '%s': %s", args.lp, e)
            sys.exit(1)
    elif args.ll:
        try:
            job = opencue.api.findJob(args.ll)
            displayLayers(job)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.ll)
            else:
                logger.error("Error retrieving layers for job '%s': %s", args.ll, e)
            sys.exit(1)
    elif args.info:
        try:
            job = opencue.api.findJob(args.info)
            cueadmin.output.displayJobInfo(job)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.info)
            else:
                logger.error("Error retrieving info for job '%s': %s", args.info, e)
            sys.exit(1)
    elif args.pause:
        job_names = format_nargs_input(args.pause)
        try:
            for job_name in job_names:
                job = opencue.api.findJob(job_name)
                if not job.isPaused():
                    job.pause()
                    logger.info("Pausing Job: %s", job.name())
                else:
                    logger.info("Job: %s is already paused", job.name())
                logger.info("---")
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", job_name)
            else:
                logger.error("Error pausing job '%s': %s", job_name, e)
            sys.exit(1)

    elif args.resume:
        job_names = format_nargs_input(args.resume)
        try:
            for job_name in job_names:
                job = opencue.api.findJob(job_name)
                job.resume()
                logger.info("Resumed Job: %s", job.name())
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", job_name)
            else:
                logger.error("Error resuming job '%s': %s", job_name, e)
            sys.exit(1)

    elif args.term:
        job_names = format_nargs_input(args.term)
        try:
            jobs = []
            for job_name in job_names:
                job = opencue.api.findJob(job_name)
                jobs.append(job)
            common.confirm("Terminate %d jobs?" % len(jobs),
                           args.force, terminateJobs, jobs)
            logger.info("Successfully terminated %d job(s)", len(jobs))
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", job_name)
            else:
                logger.error("Error terminating job '%s': %s", job_name, e)
            sys.exit(1)
    elif args.retries:
        try:
            job = opencue.api.findJob(args.retries[0])
            common.confirm("Set retries on %s to %d" % (args.retries[0], int(args.retries[1])),
                           args.force, job.setMaxRetries, int(args.retries[1]))
            logger.info("Successfully set maximum retries to %d for job: %s",
                        int(args.retries[1]), args.retries[0])
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.retries[0])
            else:
                logger.error("Error setting retries for job '%s': %s", args.retries[0], e)
            sys.exit(1)
    elif args.eat:
        try:
            job = opencue.api.findJob(args.eat)
            search = buildFrameSearch(args)
            if cueadmin.util.promptYesNo("Eat specified frames on job %s" % args.eat,
                                         args.force):
                job.eatFrames(**search)
                logger.info("Successfully ate frames for job: %s", args.eat)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.eat)
            else:
                logger.error("Error eating frames for job '%s': %s", args.eat, e)
            sys.exit(1)
    elif args.kill:
        try:
            job = opencue.api.findJob(args.kill)
            search = buildFrameSearch(args)
            if cueadmin.util.promptYesNo("Kill specified frames on job %s" % args.kill, args.force):
                job.killFrames(**search)
                logger.info("Successfully killed frames for job: %s", args.kill)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.kill)
            else:
                logger.error("Error killing frames for job '%s': %s", args.kill, e)
            sys.exit(1)
    elif args.retry:
        try:
            job = opencue.api.findJob(args.retry)
            search = buildFrameSearch(args)
            if cueadmin.util.promptYesNo("Retry specified frames on job %s" % args.retry,
                                         args.force):
                job.retryFrames(**search)
                logger.info("Successfully retried frames for job: %s", args.retry)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.retry)
            else:
                logger.error("Error retrying frames for job '%s': %s", args.retry, e)
            sys.exit(1)
    elif args.done:
        try:
            job = opencue.api.findJob(args.done)
            search = buildFrameSearch(args)
            if cueadmin.util.promptYesNo("Mark done specified frames on job %s" % args.done,
                                         args.force):
                job.markdoneFrames(**search)
                logger.info("Successfully marked frames as done for job: %s", args.done)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", args.done)
            else:
                logger.error("Error marking frames done for job '%s': %s", args.done, e)
            sys.exit(1)
    elif args.stagger:
        name, frame_range, increment = args.stagger
        try:
            job = opencue.api.findJob(name)
            layers = args.layer
            common.confirm("Stagger %s (%s) by %s" % (job.data.name, frame_range, increment),
                           args.force, staggerJob, job, layers, frame_range,
                           increment)
            logger.info("Successfully staggered frames for job: %s", job.data.name)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", name)
            else:
                logger.error("Error staggering frames for job '%s': %s", name, e)
            sys.exit(1)
    elif args.reorder:
        name, frame_range, position = args.reorder
        try:
            job = opencue.api.findJob(name)
            layers = args.layer
            common.confirm("Reorder %s (%s) to %s" % (job.data.name, frame_range, position),
                           args.force, reorderJob, job, layers, frame_range,
                           position)
            logger.info("Successfully reordered frames for job: %s", job.data.name)
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", name)
            else:
                logger.error("Error reordering frames for job '%s': %s", name, e)
            sys.exit(1)
    elif args.autoeaton:
        job_names = format_nargs_input(args.autoeaton)
        try:
            for job_name in job_names:
                job = opencue.api.findJob(job_name)
                job.setAutoEat(True)
                if job_pb2 and hasattr(job_pb2, 'DEAD'):
                    job.eatFrames(state=[job_pb2.DEAD])
                else:
                    job.eatFrames(state=['DEAD'])
                logger.info("Enabled auto-eat for job: %s", job.name())
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", job_name)
            else:
                logger.error("Error enabling auto-eat for job '%s': %s", job_name, e)
            sys.exit(1)
    elif args.autoeatoff:
        job_names = format_nargs_input(args.autoeatoff)
        try:
            for job_name in job_names:
                job = opencue.api.findJob(job_name)
                job.setAutoEat(False)
                logger.info("Disabled auto-eat for job: %s", job.name())
        except Exception as e:
            if "does not exist" in str(e).lower() or "incorrect result size" in str(e).lower():
                logger.error("Error: Job '%s' does not exist.", job_name)
            else:
                logger.error("Error disabling auto-eat for job '%s': %s", job_name, e)
            sys.exit(1)

def _get_proc_filters(args):
    """Get process filters for memory and duration.

    Args:
        args: Parsed command line arguments

    Returns:
        tuple: (procs_list, duration_range) or (None, None) if error
    """
    # Handle duration range
    if re.search(RE_PATTERN_RANGE, str(args.duration)):
        ls = args.duration.split("-")
        dur_min = common.handleIntCriterion(ls[0], common.Convert.hoursToSeconds)
        dur_max = common.handleIntCriterion(ls[-1], common.Convert.hoursToSeconds)
        if not dur_min or not dur_max:
            return None, None
        duration_range = "%s-%s" % (dur_min[-1].value, dur_max[-1].value)
    else:
        duration = common.handleIntCriterion(args.duration, common.Convert.hoursToSeconds)
        if not duration:
            return None, None
        duration_range = "0-%s" % duration[-1].value

    # Handle memory and duration filters
    if args.memory and args.duration:
        if re.search(RE_PATTERN_RANGE, str(args.memory)):
            ls = args.memory.split("-")
            mem_min = common.handleIntCriterion(int(ls[0]), common.Convert.gigsToKB)
            mem_max = common.handleIntCriterion(int(ls[1]), common.Convert.gigsToKB)
            if not mem_min or not mem_max:
                return None, None
            memory_range = "%s-%s" % (mem_min[-1].value, mem_max[-1].value)
            procs = opencue.api.getProcs(job=[args.lp],
                                       memory=memory_range,
                                       duration=duration_range)
        else:
            mem = common.handleIntCriterion(args.memory, common.Convert.gigsToKB)
            if not mem:
                return None, None
            greater_less_than_match = re.search(RE_PATTERN_GREATER_LESS_THAN,
                                               str(args.memory))
            procs = opencue.api.getProcs(job=[args.lp],
                                       memory_less_than=mem[-1].value,
                                       duration=duration_range)

            if greater_less_than_match:
                if re.search("gt", greater_less_than_match.group()):
                    procs = opencue.api.getProcs(job=[args.lp],
                                               memory_greater_than=mem[-1].value,
                                               duration=duration_range)
    else:
        # If no memory filter, just use duration filter
        procs = opencue.api.getProcs(job=[args.lp], duration=duration_range)

    return procs, duration_range


def buildFrameSearch(args):
    """Build a frame search query from command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing search parameters for frame queries
    """
    s = {}
    if args.layer:
        s["layer"] = args.layer
    if args.range:
        s["range"] = args.range
    if args.state:
        s["state"] = [common.Convert.strToFrameState(st) for st in args.state]
    if args.memory:
        mem = common.handleIntCriterion(args.memory, common.Convert.gigsToKB)
        if mem:
            if args.memory == DEFAULT_MIN_MEMORY:
                s["memory"] = "0-%s"%mem[-1].value
            else:
                s["memory"] = "%s"%mem[-1].value
    if args.duration:
        dur = common.handleIntCriterion(args.duration, common.Convert.hoursToSeconds)
        if dur:
            if args.duration == DEFAULT_MIN_DURATION:
                s["duration"] = "0-%s"%dur[-1].value
            else:
                s["duration"] = "%s"%dur[-1].value
    if args.page:
        s["page"] = args.page
    if args.limit:
        s["limit"] = args.limit
    return s

def staggerJob(job, layers, frame_range, increment):
    """Stagger frames for a job or specific layers.

    Args:
        job: Job object
        layers: List of layer names or None for all layers
        frame_range: Frame range to stagger
        increment: Stagger increment value
    """
    increment = int(increment)
    if layers:
        for layer in layers:
            _layer = opencue.api.findLayer(job, layer)
            _layer.staggerFrames(frame_range, increment)
    else:
        job.staggerFrames(frame_range, increment)

def reorderJob(job, layers, frame_range, order):
    """Reorder frames for a job or specific layers.

    Args:
        job: Job object
        layers: List of layer names or None for all layers
        frame_range: Frame range to reorder
        order: Order type (FIRST, LAST, or REVERSE)

    Raises:
        ValueError: If order is not valid
    """
    if job_pb2 and hasattr(job_pb2, 'Order'):
        valid_order = list(job_pb2.Order.keys())
    else:
        valid_order = ['FIRST', 'LAST', 'REVERSE']
    if order in valid_order:
        if layers:
            for layer in layers:
                _layer = opencue.api.findLayer(job, layer)
                _layer.reorderFrames(frame_range, order)
        else:
            job.reorderFrames(frame_range, order)
    else:
        raise ValueError("Invalid ordering: '%s', must be FIRST, LAST, or REVERSE" % order)

def displayLayers(job):
    """Display layers for a job.

    Args:
        job: Job object to display layers for
    """
    layers = job.getLayers()
    print("Job: %s has %d layers\n" % (job.data.name, len(layers)))

    layer_format = "%-30s %-8s %-8s %-8s %-8s %-8s"
    header = layer_format % ("Layer", "Total", "Done", "Running", "Waiting", "Failed")
    print(header)
    print("-" * len(header))

    for layer in layers:
        print(layer_format % (
            layer.data.name[:29],  # Truncate long layer names
            layer.data.layer_stats.total_frames,
            layer.data.layer_stats.succeeded_frames,
            layer.data.layer_stats.running_frames,
            layer.data.layer_stats.waiting_frames,
            layer.data.layer_stats.dead_frames
        ))
        if layer.data.tags:
            print("   tags: %s" % ' | '.join(layer.data.tags))
        print("")

def terminateJobs(jobs):
    """Terminate a list of jobs with proper reason tracking.

    Args:
        jobs: List of job objects to terminate
    """
    for job in jobs:
        job.kill(reason=KILL_REASON)
        logger.info(KILL_REASON, job.name(), getpass.getuser())
        logger.info("---")

---
title: "pycuerun command"
layout: default
parent: Reference
nav_order: 41
linkTitle: "pycuerun command"
date: 2019-05-23
description: >
  Submit and launch OpenCue jobs
---

# pycuerun command

### Submit and launch OpenCue jobs

---

This page lists the arguments and flags you can specify for the `pycuerun`
command. You can run `pycuerun` to launch OpenCue outline jobs and frames.
To submit a job to OpenCue, you must first create an outline script.

The command expects the following usage pattern:

```shell
pycuerun [options] outline_script [frame range]
```

To run the command, you must provide an outline script.

## Help options
  
### `-h`, `--help`

Show this help message and exit.

## Standard options

### `-b BACKEND` and `--backend=BACKEND`

Arguments: The name of an existing backend.

Set the backend for the job.

### `-s SERVER` and `--server=SERVER`

Arguments: The name of an existing server.

Set the server for the job.

### `-F FACILITY` and `--facility=FACILITY`

Arguments: The name of an existing facility.

Set the job facility.

### `-V` and `--verbose`

Enable verbose output.

### `-D` and `--debug`

Turn on debugging.

## Development options

### `-v VERSION` and `--version=VERSION`

Arguments: The name of an existing facility.

### `-r REPOS` and `--repos=REPOS`

Arguments: The name of a repository.

### `--dev`

Add current user's dev areas to python path.

### `--dev-user=DEVUSER`

Arguments: A user's dev area.

Add given user's dev areas to python path.
  
### `--env=ENV`

Arguments: A key/value pair.

Add environment key/value pairs with `--env k=v`.

## Job options

### `-p` and `--pause`

Launch outline script in paused state.

### `-w` and `--wait`

Block until the launched job is completed.

### `-t` and `--test`

Block until the job is completed or failed.

### `-f RANGE` and `--range=RANGE`

Arguments: A range of frames.

Specify the frame range. Defaults to `$FR` env variable.

### `--shot=SHOT`

Switch job to the specified shot.

### `--no-mail`

Disable email notifications.

### `--max-retries=MAXRETRIES`

Arguments: The maximum number of retries per frame.

Set the max number of retries per frame.

### `-o OS` and `--os=OS`

Arguments: An operating system.

Set the target operating system for the job.

###  `--base-name=BASENAME`

Arguments: The base name for the job.

Set the base name for the job.

### `--autoeat`

Automatically eat dead frames with no retry.

### `--qc`

Allow artist to QC to the job before the job leaves the cue on completion.

## Frame execution options

### `-e FRAME_NAME` and `--execute=FRAME_NAME`

Arguments: The name of a frame.

Execute the given frame.  Example: `1-bty_all`

### `-i SCRIPT` and `--inspect=SCRIPT`

Arguments: The name of an outline script.

Dump some information on the given outline script.

### `-u USER` and `--user=USER`

Arguments: A username.

Set the user to run as.

### `-j JOB_ID` and `--jobid=JOB_ID`

Arguments: The base name of a job. 

Specify the basename of the job associated with an outline.

### `-m MAX_RETRIES` and `--maxretries=MAX_RETRIES`

Arguments: The maximum number of retries for this job.

Specify max retries for this job.

## Plugin options

### `-L RUN_LOCAL` and `--run-local=RUN_LOCAL`

Arguments: `RUN_LOCAL`

Run local cores.

### `-T RUN_LOCAL_THREADS` and `--run-local-threads=RUN_LOCAL_THREADS`

Arguments: `RUN_LOCAL_THREADS`

Set number of threads for local cores to run per frame.

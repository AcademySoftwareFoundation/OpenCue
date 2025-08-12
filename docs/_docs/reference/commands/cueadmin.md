---
title: "cueadmin command"
layout: default
parent: Reference
nav_order: 40
linkTitle: "cueadmin command"
date: 2025-08-11
description: >
  Administer your OpenCue deployment
---

# cueadmin command

### Administer your OpenCue deployment

---

This page lists the arguments and flags you can specify for the `cueadmin`
command. You can run `cueadmin` to administer and monitor your OpenCue
deployment from the command line.

For comprehensive documentation including examples and workflows, see:
- **[CueAdmin Tool Reference](/docs/reference/tools/cueadmin/)** - Detailed guide with examples
- **[CueAdmin Tutorial](/docs/tutorials/cueadmin-tutorial/)** - Step-by-step learning guide

## Optional arguments

### `-h` and `--help`

Show the help message and exit.

## General Options

### `-server`

Arguments: `HOSTNAME [HOSTNAME ...]`

Specify cuebot address(es).

### `-facility`

Arguments: `CODE`

Specify the facility code.

### `-verbose` and `-v`

Turn on verbose logging.

### `-force`

Force operations that usually require confirmation.

## Query Options

### `-lj` and `-laj`

Arguments: `[SUBSTR [SUBSTR ...]]`

List jobs with optional name substring match.

### `-lji`

Arguments: `[SUBSTR [SUBSTR ...]]`

List job info with optional name substring match.

### `-ls`

List shows.

### `-la`

List allocations.

### `-lb`

Arguments: `SHOW [SHOW ...]`

List subscriptions for specified shows.

### `-lba`

Arguments: `ALLOC`

List all subscriptions to a specified allocation.

### `-lp` and `-lap`

Arguments: `[SHOW ...] [-host HOST ...] [-alloc ...] [-job JOB ...] [-memory ...] [-limit ...]`

List running procs. Optionally filter by show, host, memory, alloc. Use
`-limit` to limit the results to N procs.

### `-ll` and `-lal`

Arguments: `[SHOW ...] [-host HOST ...] [-alloc ...] [-job JOB ...] [-memory ...] [-limit ...]`

List running frame log paths. Optionally filter by show, host, memory, alloc.
Use `-limit` to limit the results to N logs.

### `-lh`

Arguments: `[SUBSTR ...] [-state STATE] [-alloc ALLOC]`

List hosts with optional name substring match.

### `-lv`

Arguments: `[SHOW]`

List default services or show-specific service overrides.

## Filter Options

### `-job`

Arguments: `JOB [JOB ...]`

Filter proc or log search by job

### `-alloc`

Arguments: `ALLOC [ALLOC ...]`

Filter host or proc search by allocation

### `-memory`

Arguments: `MEMORY`

Filters a list of procs by the amount of reserved memory. Memory
can be specified in one of 3 ways. As a range, `<min>-<max>`. Less than,
`lt<value>`. Greater than, `gt<value>`. Values should be specified in GB.

### `-duration`

Arguments: `DURATION`

Show procs that have been running longer than the specified number of
hours or within a specific time frame. Ex. `-time 1.2` or `-time 3.5-4.5`.
Waiting frames are automatically filtered out.

### `-limit`

Arguments: `LIMIT`

Limit the result of a proc search to N rows

## Show Options

### `-create-show`

Arguments: `SHOW`

Create a new show.

### `-delete-show`

Arguments: `SHOW`

Delete specified show.

### `-disable-show`

Arguments: `SHOW`

Disable the specified show.

### `-enable-show`

Arguments: `SHOW`

Enable the specified show.

### `-dispatching`

Arguments: `SHOW ON|OFF`

Enables or disables frame dispatching on the specified show.

### `-booking`

Arguments: `SHOW ON|OFF`

Booking is new proc assignment. If booking is disabled, procs will continue to
run on existing jobs but no new jobs will be booked.

### `-default-min-cores`

Arguments: `SHOW CORES`

The default min core value for all jobs before any min core filters are applied.

### `-default-max-cores`

Arguments: `SHOW CORES`

The default max core value for all jobs before any max core filters are applied.

## Allocation Options

### `-create-alloc`

Arguments: `FACILITY ALLOC TAG`

Create a new allocation.

### `-delete-alloc`

Arguments: `NAME`

Delete an allocation. It must be empty.

### `-rename-alloc`

Arguments: `OLD NEW`

Rename allocation. New name must not contain facility prefix.

### `-transfer`

Arguments: `OLD NEW`

Move all hosts from source allocation to destination allocation.

### `-tag-alloc`

Arguments: `ALLOC TAG`

Tag allocation.

## Subscription Options

### `-create-sub`

Arguments: `SHOW ALLOC SIZE BURST`

Create new subscription.

### `-delete-sub`

Arguments: `SHOW ALLOC`

Delete subscription.

### `-size`

Arguments: `SHOW ALLOC SIZE`

Set the guaranteed number of cores.

### `-burst`

Arguments: `SHOW ALLOC BURST`

Set the number of burst cores. Use the percent sign to indicate a
percentage of the subscription size instead of a hard size.

## Host Options

### `-host`

Arguments: `HOSTNAME [HOSTNAME ...]`

Specify the host names to operate on.

### `-hostmatch` and `-hm`

Arguments: `SUBSTR [SUBSTR ...]`

Specify a list of substring matches to match groups of hosts.

### `-lock`

Lock hosts.

### `-unlock`

Unlock hosts.

### `-move`

Arguments: `ALLOC`

Move hosts into a new allocation.

### `-delete-host`

Delete hosts.

### `-safe-reboot`

Lock and reboot hosts when idle.

### `-repair`

Sets hosts into the repair state.

### `-fixed`

Sets hosts into Up state.

### `-thread`

Arguments: `{auto,all,variable}`

Set the host's thread mode.

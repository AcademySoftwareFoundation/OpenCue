---
title: "Glossary"
nav_order: 11
parent: Concepts
layout: default
linkTitle: "Glossary"
date: 2019-02-22
description: >
  Glossary of common OpenCue terms
---

# Glossary

### Glossary of common OpenCue terms

---

This page defines common terminology for OpenCue.

## Allocation

An allocation is a group for organizing render *hosts* by associating them with
a *facility* and a *tag*. Render hosts exist within an allocation and inherit
their facility and a tag from the allocation.

## Cores

The processing units that make up a *proc*.

## Cue

A nickname for the entire queuing system, which also prefixes the names of
OpenCue rendering tools, such as *CueGUI* and *Cuebot*.

## CueAdmin

Command-line administrative tools for OpenCue system management, providing
scripting capabilities for automation, bulk operations, and system maintenance
tasks. Written in Python and provides a thin layer over the OpenCue Python API,
*PyCue*.

## Cuebot

The central management server that performs critical OpenCue tasks including
managing job submissions, distributing work to render nodes, and responding to
API requests from client tools. Typically runs on a server and can be deployed
in clusters for high availability.

## CueGUI

The desktop graphical user interface divided into two main workspaces: Cuetopia
(artist-focused job monitoring) and CueCommander (administrator-focused system
management). Provides comprehensive tools for job monitoring, frame inspection,
host management, and system administration.

## Cueman

A specialized tool for managing and monitoring OpenCue deployments, providing
additional administrative capabilities and system oversight functions.

## CueSubmit

A graphical user interface for configuring and launching rendering jobs.
Typically runs as a plug-in within 3D software like Maya, Blender, or Nuke,
allowing artists to submit jobs directly from their creative applications.

## CueWeb

A web-based interface that brings CueGUI's core functionality to the browser.
Offers job management, frame monitoring, real-time updates, and collaborative
features accessible from anywhere on the network without requiring client
installation.

## CueNIMBY

A cross-platform system tray application for workstation NIMBY control. Provides
users with visual feedback and manual control over their machine's rendering
availability. Shows real-time state through color-coded icons, sends desktop
notifications when jobs start, and supports time-based scheduling for automatic
state changes. Works alongside *RQD*'s automatic NIMBY feature.

## Dependent job

A *job* which won't run until the frames of another job are completed.

## Facility

Facilities can be used to label and separate farm resources. This is generally
done based on physical locations to help guide jobs to hosts in that location.
Both *jobs* and *allocations* belong to a facility. Jobs submitted to a facility
will only run on allocations within that same facility.

## Frames

An individual command that's contained in a *layer*.

## Hard dependency

A frame-to-frame dependency, where only the corresponding *frames* need to
finish.

## Host

A machine that is running an instance of *rqd*. This machine will split up into
*procs* to execute work.

## Job

A job is a collection of *layers*, which is sent as a *script* to the queue to
be processed on remote *cores*.

## Layers

The sub-jobs in an *outline script* job. Each layer contains a frame range and a
command to execute.

## Outline script

A powerful tool for submitting *jobs* to the *queue*. You can define an
outline script to batch multiple job submissions into a single job, setting up
dependencies and / or running in parallel. Outline scripts can submit almost any
type of job to the cue, including Maya, Katana, or even shell commands.

## Proc

A proc is a slot on a render *host* that has been carved out and isolated to
execute a *frame*.

## OpenCue REST Gateway

A production-ready HTTP service that translates REST API calls to gRPC
communication with Cuebot. Enables web applications, scripts, and third-party
tools to interact with OpenCue services through standard HTTP endpoints.

## PyCue

The Python API library that provides programmatic access to OpenCue
functionality. Used by client applications and custom scripts to interact with
Cuebot's gRPC interface. OpenCue client-side Python tools, such as *CueGUI* and
*CueAdmin*, all use PyCue for communicating with your OpenCue deployment.

## PyOutline

A Python library for creating job specifications and render job descriptions.
Provides the framework for defining complex rendering workflows and job
dependencies. It provides a Python interface to the job specification XML,
allowing you to construct complex jobs with Python code instead of working
directly with XML. *CueSubmit* uses PyOutline to construct its job submissions.

## Queue

A queue is a render farm that processes a large number of render *jobs*
according to defined priorities.

## RQD (Python)

The render queue daemon that runs on all rendering hosts. RQD registers hosts
with Cuebot, receives work instructions, monitors worker processes, and reports
results back to the central server. This is the original Python implementation.

## Rust RQD

A high-performance implementation of RQD written in Rust, providing the same
functionality as Python RQD with improved performance and resource efficiency.

## Service

A service is a collection of resource requirements and tags that are associated
with a *layer*. The service contains minimum and maximum thread requirements,
minimum memory and gpu requirements, whether the jobs are threadable or not, and
a list of tags. These attributes are inherited by *layers* submitted to that
service by default. Services can be used to setup different requirements for
different software jobs. For instance, a Maya render may need 6GB of memory vs a
Nuke render may only need 2GB.

## Show

A show is a group of related work to be done. *Jobs* submitted to OpenCue exist
within a show. *Subscriptions* list the available *allocations* to a given show.

Shows can be **archived** to consolidate resources. When a show is archived, it is
aliased to another show, allowing jobs submitted to the archived show to run on the
target show's allocations. This is useful for wrapped productions that may need
occasional reruns or for redirecting legacy content to training allocations.

## Soft dependency

When all the *frames* of the first *job* need to finish before the second job
can begin.

## Subscription

A Subscription is an object that associates multiple *allocations* with a
*show*. This drives what render *hosts* can do work for a show.

## Tag

A string that can be assigned to a render *host* and a *layer*. Frames contained
in a layer with a tag will only render on a host that also shares that tag.

## Relationships

![OpenCue relationships](/assets/images/opencue_object_relations.png)

This diagram depicts the connections between the primary objects within OpenCue
As you can see the majority of connections follow a one-to-many type of
relationship. For example, a *job* can be connected to many *layers*. With the
understanding that a *frame* can only run on a *proc* that shares the same *tag*
and *facility*, you can walk this diagram to determine where these settings are
coming from in your jobs.

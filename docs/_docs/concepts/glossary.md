---
title: "Glossary"
nav_order: 8
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

CueAdmin is the OpenCue command-line client. You run this client to administer
an OpenCue deployment. It's written in Python and provides a thin layer over the
OpenCue Python API, *PyCue*.

## Cuebot

Cuebot is a utility that runs in the background on a workstation or server
cluster and performs a variety of important OpenCue management tasks.

## CueSubmit

CueSubmit is a graphical user interface for configuring and launching rendering
jobs to an OpenCue deployment.

## CueGUI

A graphical user interface you run to monitor and manage *jobs*, *layers*, and
*frames*.

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

## PyCue

PyCue is the OpenCue Python API. OpenCue client-side Python tools, such as
*CueGUI* and *CueAdmin*, all use PyCue for communicating with your OpenCue
deployment.

## PyOutline

PyOutline is a Python library. It provides a Python interface to the job
specification XML, allowing you to construct complex jobs with Python code
instead of working directly with XML. *CueSubmit* uses PyOutline to construct
its job submissions.

## Queue

A queue is a render farm that processes a large number of render *jobs*
according to defined priorities.

## RQD

RQD is a client daemon that runs on all hosts that are doing work for an OpenCue
deployment.

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

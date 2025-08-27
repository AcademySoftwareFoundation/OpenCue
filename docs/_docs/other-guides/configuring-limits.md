---
title: "Configuring limits"
layout: default
parent: Other Guides
nav_order: 29
linkTitle: "Configuring limits"
date: 2020-03-26
description: >
  Configure limits to set max number of concurrently running frames
---

# Configuring Limits

### Configure limits to set max number of concurrently running frames

---

This page describes how to configure limits which allow users to specify 
the maximum number of concurrently running frames associated with that limit.
Limits are specified on the Job Layer and all Frames within that Layer are 
considered to take 1 limit count. After the total limit count reaches the 
configured max value, the dispatcher will stop any additional frames from 
running until a frame with that limit has completed.

## Configuring a new limit

You can set a new limit by following these steps:

1.  Open CueGUI.

1.  Load **Limits** view from the **Views/Plugins->Cuecommander** menu.

1.  Click **Add Limit** button in the **Limits** view.

1. Enter a name for the new limit and press **OK**.

1. Right-click on the newly created limit and select **Edit Max Value**.

1. Enter the desired maximum number of concurrenstly running frames for this limit.

1. Your limit is now configured and ready for use. New submissions will be able select this limit in CueSubmit UI when creating a new job.

## What's next?
*  [Add or remove limits from existing layers.](/docs/user-guides/adding-removing-limits/)

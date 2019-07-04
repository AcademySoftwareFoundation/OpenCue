# Cuebot

Cuebot typically runs on a server and performs a variety of important OpenCue management
tasks, including:

- Managing OpenCue jobs and job submissions.
- Distributing work to render nodes.
- Responding to API requests from client-side tools such as CueGUI.

A typical OpenCue deployment runs a single instance of Cuebot, which is shared by all users.

## Deployment Instructions

For instructions on deploying a Cuebot instance see
[Deploying Cuebot](https://github.com/imageworks/OpenCue/wiki/Deploying-Cuebot) on the Wiki.

## Development Setup

This section covers setting up a development environment in IntelliJ.

NOTE: Only OpenCue developers will need to do this setup. If you just want to use Cuebot, follow
[Deployment Instructions](#deployment-instructions).

### Import Project

- From the IntelliJ launch screen, choose "Import Project".
- Browse to the `OpenCue/cuebot` directory. Don't select any files. Click "Open".
- Choose "Import project from external model" > "gradle". This will initialize the project from
  what's checked in already.
- Default Gradle options are typically fine.

### Configure IntelliJ Project

- Import our code style XML. IntelliJ Preferences > Editor > Code Style > Java >
  Scheme (gear dropdown) > Import Scheme > IntelliJ IDEA code style XML.
  Select `code_style_ij.xml`.
- Delegate build commands to Gradle. IntelliJ Preferences > Build, Execution, Deployment >
  Build Tools > Gradle > Runner. Check "Delegate IDE build/run actions to gradle".

### Build the Project

View > Tool Windows > Gradle. Refresh the Gradle project and run the build task, which will
run compilation and tests.

# Cuebot

Cuebot is the "brains" of OpenCue. It manages all jobs and job submissions, and
distributes work to render nodes.

## Development Setup

This covers setting up a development environment in IntelliJ.

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


# Cue3Bot

CueBot is the "brains" of Cue3. It manages all jobs and job submissions, and
distributes work to render nodes.

## Development Setup

This covers setting up a development environment in IntelliJ.

### Install Dependencies

#### ICE

- Install ICE 3.6 on your machine.

  On Debian or Ubuntu Linux you can install via apt:

  ```
  sudo apt-get update
  sudo apt-get install zeroc-ice-all-runtime zeroc-ice-all-dev
  ```

  On OS X, ensure Xcode Commandline Tools are installed then install via Homebrew:

  ```
  sudo xcode-select --install
  brew tap zeroc-ice/tap
  brew install zeroc-ice/tap/ice36
  ```
 
- Download and install the SBT ICE plugin.

  ```
  export BUCKET_NAME=queue-manager-third-party
  cd cue3/cue3bot/project/maven/
  gsutil cp gs://$BUCKET_NAME/sbt-zeroc-ice_2.10_0.13.tar.gz ./
  tar xvzf sbt-zeroc-ice_2.10_0.13.tar.gz
  rm sbt-zeroc-ice_2.10_0.13.tar.gz
  ```

#### Oracle

##### OS X

Install the Oracle Instant Client libraries.

- Download Instant Client 12.1 from
  [this page](http://www.oracle.com/technetwork/database/features/instant-client/index-097480.html).
- Copy the files into `java.library.path`.

  ```
  mkdir -p ~/Library/Java/Extensions/
  cp ~/Downloads/instantclient_12_1/* ~/Library/Java/Extensions/
  ```

#### gRPC

TODO: Linux.

On OS X, use Homebrew to install the main protobuf compiler, then manually build and install
the java generator.

```
brew install protobuf
curl -#sL "https://github.com/grpc/grpc-java/archive/v1.14.0.tar.gz" | tar -xz
cd grpc-java-1.14.0/compiler/
export PROTOBUF_LIB="$(brew --prefix)/Cellar/protobuf/3.6.1"
CXXFLAGS="-I$PROTOBUF_LIB/include" LDFLAGS="-L$PROTOBUF_LIB/lib" ../gradlew java_pluginExecutable
cp build/exe/java_plugin/protoc-gen-grpc-java $(brew --prefix)/bin/
cd ../../
rm -rf grpc-java-1.14.0/
```

### Import Project

- Install the IntelliJ Scala plugin (NOT the sbt plugin; sbt support is included with the Scala
  plugin).
- From the IntelliJ launch screen, choose "Import Project".
- Browse to the `cue3/cue3bot` directory. Don't select any files. Click "Open".
- Choose "Import project from external model" > "sbt". This will initialize the project from what's
  checked in already.
- Choose to build the project with JDK 1.8 if it's not selected already. Other default options
  should be fine.

### Build the Project

- `View > Tool Windows > sbt > Refresh all sbt projects` will update the sbt project. This is done
  by default when you first import the project.
- `View > Tool Windows > sbt shell` will run an sbt shell within IntelliJ. Run `compile` to run
  tasks from `build.sbt`; this includes generating Java code from the ICE slice files and is
  necessary before compiling the rest of the Java code.
- `Build > Rebuild Project` will compile the rest of the Java code.


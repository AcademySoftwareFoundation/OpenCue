import sbt._
import Keys._

object BuildSettings {
  val buildSettings = Defaults.defaultSettings ++ Seq(
    organization := "com.imageworks"
  )
}

object MyBuild extends Build {
  import BuildSettings._

  var PATH_PROTOC = "/usr/bin/protoc"
  if (System.getProperty("os.name") == "Mac OS X") {
    PATH_PROTOC = System.getProperty("user.home") + "/homebrew/bin/protoc"
  }

  lazy val root = Project(
    "cuebot",
    file("."),
    settings = buildSettings
  )

  val deployTask = TaskKey[Unit]("deploy", "Build and deploy to the development servers.")

  /**
   * Modify the xerial.sbt.Pack.pack task to add extra post processing.
   */
  def patchPack: Seq[Setting[_]] = Seq(
    xerial.sbt.Pack.pack <<= (xerial.sbt.Pack.pack, baseDirectory) map { (distDir, base) =>
      import xerial.sbt.Pack._

      // Inject custom code into generated binary
      val binDir: File = distDir / "bin"
      val bin = IO.read(binDir / "cuebot")
      val lines = bin.split("\\r?\\n")
      val buf = new StringBuilder
      buf.append(lines(0) + "\n")
      buf.append("""
export ORACLE_HOME=/usr/lib/oracle/12.1
export LD_LIBRARY_PATH=${ORACLE_HOME}:${ORACLE_HOME}/client64/lib
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib64
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/share
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/lib
export TNS_ADMIN=/opt/tns

""")
      lines.drop(1).foreach(line => buf.append(line + "\n"))
      IO.write(binDir / "cuebot", buf.toString)

      // Create conf directory
      val confDir: File = distDir / "conf"
      confDir.mkdirs()

      // Create stub directories
      for (d <- Seq("logs", "storage", "var")) {
        val f: File = distDir / d
        f.mkdirs()
        s"""/bin/touch ${f / ".keep"}""" !
      }

      distDir
    }
  )
}

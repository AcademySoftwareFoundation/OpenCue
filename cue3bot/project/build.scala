import sbt._
import Keys._
import sbtzerocice.{ZeroCIcePlugin=>Ice}

object BuildSettings {
  val buildSettings = Defaults.defaultSettings ++ Seq(
    organization := "com.imageworks"
  )
}

object MyBuild extends Build {
  import BuildSettings._

  val iceHome = SettingKey[String]("ice-home")
  val iceBinDir = SettingKey[String]("ice-bin-dir")
  val iceSliceDir = SettingKey[String]("ice-slice-dir")

  lazy val root = Project(
    "cuebot",
    file("."),
    settings = buildSettings ++ Seq(
      iceHome := "/usr",
      iceBinDir := iceHome.value + "/bin",
      iceSliceDir := iceHome.value + "/share/Ice-3.6.1/slice"
    )
  )

  val deployTask = TaskKey[Unit]("deploy", "Build and deploy to the development servers.")

  val MainSlice = config("main-slice") extend(Compile)

  def genSliceSettings: Seq[Setting[_]] = {
    import Ice.IceKeys._
    import Keys._

    def customMainSettings: Seq[Setting[_]] = Seq(
      slice2javaBin := "%s/slice2java" format iceBinDir.value,
      includePaths += file(iceSliceDir.value),
      includePaths <++= (sourceDirectory) map { x =>
        x / "spi" :: x / "cue" :: Nil }
    )

    Ice.zerociceSettingsIn(MainSlice) ++
      inConfig(MainSlice)(inTask(slice2java)(customMainSettings))
  }

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
# These lines come from code in project/build.scala.
export ORACLE_HOME=/usr/lib64/oracle-instantclient-11.2
export LD_LIBRARY_PATH=/shots/spi/home/java/FileSequence/x86_64/v6/rhel7/:${ORACLE_HOME}
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

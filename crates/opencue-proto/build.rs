use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    build_protobuf()
}

fn build_protobuf() -> Result<(), Box<dyn std::error::Error>> {
    let protos_dir = PathBuf::from("src/protos");
    let crate_dir = PathBuf::from("src");
    let mut proto_files = Vec::<String>::new();

    let subdir_proto_files: Vec<String> = std::fs::read_dir(&protos_dir)?
        .map(|dir| protos_dir.join(dir.unwrap().file_name()))
        .filter(|entry| {
            if Some(std::ffi::OsStr::new("out")) == entry.file_name() {
                return false;
            }
            if let Some(extension) = entry.extension() {
                return extension == "proto";
            }
            false
        })
        .map(|path| path.to_string_lossy().to_string())
        .collect();
    proto_files.extend(subdir_proto_files);

    // Identify the parent directory of the where the generated sources
    // live to catch the case where the generated sources are
    // deleted or new protos are added
    println!("cargo:rerun-if-changed=src/protos");
    for name in &proto_files {
        println!("cargo:rerun-if-changed={}", name);
    }
    tonic_build::configure()
        // .type_attribute("Host", "#[derive(Copy)]")
        // .type_attribute("Frame", "#[derive(Copy)]")
        // .type_attribute("LookupResponse", "#[derive(Eq, Hash)]")
        // .type_attribute("Entry", "#[derive(Eq, Hash)]")
        // .type_attribute("Entry.kind", "#[derive(Eq, Hash)]")
        // .type_attribute("LinkTreeEntry", "#[derive(Eq, Hash)]")
        // .type_attribute("BranchPoint", "#[derive(Eq, Hash)]")
        // .type_attribute("Volume", "#[derive(Eq, Hash)]")
        // .type_attribute("Volume.kind", "#[derive(Eq, Hash)]")
        // .type_attribute("LocalVolume", "#[derive(Eq, Hash)]")
        // .type_attribute("ConnectionConfig", "#[derive(Eq, Hash)]")
        // .type_attribute("ConnectionConfig.kind", "#[derive(Eq, Hash)]")
        // .type_attribute("NFSConnection", "#[derive(Eq, Hash)]")
        .out_dir(&crate_dir)
        .compile(
            proto_files.as_slice(),
            &[protos_dir.to_string_lossy().to_string()],
        )?;
    Ok(())
}

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
        .filter(|entry| entry.is_file() && entry.extension().is_some_and(|ext| ext == "proto"))
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
        .type_attribute("Stat", "#[derive(serde::Deserialize, serde::Serialize)]")
        .type_attribute("Statm", "#[derive(serde::Deserialize, serde::Serialize)]")
        .type_attribute("Status", "#[derive(serde::Deserialize, serde::Serialize)]")
        .type_attribute(
            "ProcStats",
            "#[derive(serde::Deserialize, serde::Serialize)]",
        )
        .type_attribute(
            "ChildrenProcStats",
            "#[derive(serde::Deserialize, serde::Serialize)]",
        )
        .type_attribute(
            "RunFrame.uid_optional",
            "#[derive(serde::Deserialize, serde::Serialize)]",
        )
        .type_attribute(
            "RunFrame",
            "#[derive(serde::Deserialize, serde::Serialize)]",
        )
        .out_dir(&crate_dir)
        .compile_protos(
            proto_files.as_slice(),
            &[protos_dir.to_string_lossy().to_string()],
        )?;
    Ok(())
}

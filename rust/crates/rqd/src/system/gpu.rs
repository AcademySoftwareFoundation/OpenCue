use miette::Result;
use opencue_proto::host::{GpuDevice, GpuUsage};
use std::collections::HashMap;
use tracing::{error, info, warn};

/// Abstract GPU discovery interface
pub trait GpuDiscovery {
    /// Detect GPU devices on this machine
    fn detect_devices(&self) -> Result<Vec<GpuDevice>>;

    /// Get current utilization for a specific GPU device
    fn get_utilization(&self, device_id: &str) -> Result<GpuUsage>;
}

/// NVIDIA GPU discovery using NVML library
pub struct NvidiaGpuDiscovery {
    nvml_available: bool,
}

impl NvidiaGpuDiscovery {
    pub fn new() -> Self {
        let nvml_available = Self::check_nvml_available();
        if nvml_available {
            info!("Using NVML for NVIDIA GPU discovery");
        } else {
            warn!("NVML unavailable, GPU features will be limited");
        }
        Self { nvml_available }
    }

    fn check_nvml_available() -> bool {
        #[cfg(feature = "nvml")]
        {
            match nvml_wrapper::Nvml::init() {
                Ok(_) => true,
                Err(e) => {
                    warn!("NVML initialization failed: {}", e);
                    false
                }
            }
        }
        #[cfg(not(feature = "nvml"))]
        {
            false
        }
    }

    #[cfg(feature = "nvml")]
    fn detect_via_nvml(&self) -> Result<Vec<GpuDevice>> {
        use nvml_wrapper::Nvml;

        let nvml = Nvml::init().map_err(|e| miette::miette!("NVML init failed: {}", e))?;
        let device_count = nvml.device_count().map_err(|e| miette::miette!("Failed to get device count: {}", e))?;

        let mut devices = Vec::new();
        for i in 0..device_count {
            match nvml.device_by_index(i) {
                Ok(device) => {
                    let name = device.name().unwrap_or_else(|_| "Unknown".to_string());
                    let memory_info = device.memory_info().ok();
                    let pci_info = device.pci_info().ok();
                    let driver_version = nvml.sys_driver_version().unwrap_or_else(|_| "Unknown".to_string());
                    let cuda_version = nvml.sys_cuda_driver_version().ok();

                    let gpu_device = GpuDevice {
                        id: i.to_string(),
                        vendor: "NVIDIA".to_string(),
                        model: name,
                        memory_bytes: memory_info.map(|m| m.total).unwrap_or(0),
                        pci_bus: pci_info.map(|p| p.bus_id).unwrap_or_else(|| "Unknown".to_string()),
                        driver_version,
                        cuda_version: cuda_version.map(|v| format!("{}.{}", v / 1000, (v % 1000) / 10)).unwrap_or_else(|| "Unknown".to_string()),
                        attributes: HashMap::new(),
                    };
                    devices.push(gpu_device);
                }
                Err(e) => {
                    warn!("Failed to get device {}: {}", i, e);
                }
            }
        }
        Ok(devices)
    }

    #[cfg(not(feature = "nvml"))]
    fn detect_via_nvml(&self) -> Result<Vec<GpuDevice>> {
        Ok(Vec::new())
    }

    fn detect_via_smi(&self) -> Result<Vec<GpuDevice>> {
        use std::process::Command;

        let output = Command::new("nvidia-smi")
            .args(&[
                "--query-gpu=index,name,memory.total,pci.bus_id,driver_version",
                "--format=csv,noheader,nounits",
            ])
            .output()
            .map_err(|e| miette::miette!("Failed to run nvidia-smi: {}", e))?;

        if !output.status.success() {
            return Err(miette::miette!("nvidia-smi command failed"));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut devices = Vec::new();

        for line in stdout.lines() {
            let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();
            if parts.len() >= 5 {
                let memory_mb: f64 = parts[2].parse().unwrap_or(0.0);
                let memory_bytes = (memory_mb * 1_048_576.0) as u64; // MB to bytes

                let gpu_device = GpuDevice {
                    id: parts[0].to_string(),
                    vendor: "NVIDIA".to_string(),
                    model: parts[1].to_string(),
                    memory_bytes,
                    pci_bus: parts[3].to_string(),
                    driver_version: parts[4].to_string(),
                    cuda_version: "Unknown".to_string(),
                    attributes: HashMap::new(),
                };
                devices.push(gpu_device);
            }
        }

        Ok(devices)
    }
}

impl GpuDiscovery for NvidiaGpuDiscovery {
    fn detect_devices(&self) -> Result<Vec<GpuDevice>> {
        if self.nvml_available {
            self.detect_via_nvml()
        } else {
            self.detect_via_smi()
        }
    }

    fn get_utilization(&self, device_id: &str) -> Result<GpuUsage> {
        #[cfg(feature = "nvml")]
        {
            if self.nvml_available {
                use nvml_wrapper::Nvml;

                let nvml = Nvml::init().map_err(|e| miette::miette!("NVML init failed: {}", e))?;
                let index: u32 = device_id.parse().map_err(|e| miette::miette!("Invalid device ID: {}", e))?;
                let device = nvml.device_by_index(index).map_err(|e| miette::miette!("Device not found: {}", e))?;

                let utilization = device.utilization_rates().ok();
                let memory_info = device.memory_info().ok();
                let temperature = device.temperature(nvml_wrapper::enum_wrappers::device::TemperatureSensor::Gpu).ok();

                return Ok(GpuUsage {
                    device_id: device_id.to_string(),
                    utilization_pct: utilization.map(|u| u.gpu).unwrap_or(0),
                    memory_used_bytes: memory_info.map(|m| m.used).unwrap_or(0),
                    temperature_c: temperature.unwrap_or(0),
                });
            }
        }

        // Fallback: return empty usage
        Ok(GpuUsage {
            device_id: device_id.to_string(),
            utilization_pct: 0,
            memory_used_bytes: 0,
            temperature_c: 0,
        })
    }
}

/// Apple Metal GPU discovery for macOS
pub struct AppleMetalGpuDiscovery;

impl AppleMetalGpuDiscovery {
    pub fn new() -> Self {
        Self
    }

    fn parse_vram(vram_str: &str) -> u64 {
        // Parse strings like "16 GB" or "16384 MB" to bytes
        let parts: Vec<&str> = vram_str.split_whitespace().collect();
        if parts.len() >= 2 {
            if let Ok(value) = parts[0].parse::<u64>() {
                match parts[1] {
                    "GB" => return value * 1024 * 1024 * 1024,
                    "MB" => return value * 1024 * 1024,
                    _ => {}
                }
            }
        }
        0
    }
}

impl GpuDiscovery for AppleMetalGpuDiscovery {
    fn detect_devices(&self) -> Result<Vec<GpuDevice>> {
        use std::process::Command;

        let output = Command::new("system_profiler")
            .args(&["SPDisplaysDataType", "-json"])
            .output()
            .map_err(|e| miette::miette!("Failed to run system_profiler: {}", e))?;

        if !output.status.success() {
            return Err(miette::miette!("system_profiler command failed"));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let json_data: serde_json::Value = serde_json::from_str(&stdout)
            .map_err(|e| miette::miette!("Failed to parse JSON: {}", e))?;

        let mut devices = Vec::new();
        let mut gpu_idx = 0;

        if let Some(displays) = json_data["SPDisplaysDataType"].as_array() {
            for display in displays {
                let chipset_model = display["sppci_model"]
                    .as_str()
                    .unwrap_or("Unknown")
                    .to_string();
                let vram = display["spdisplays_vram"]
                    .as_str()
                    .unwrap_or("0 MB")
                    .to_string();
                let vram_bytes = Self::parse_vram(&vram);

                let mut attributes = HashMap::new();
                attributes.insert("metal_supported".to_string(), "true".to_string());

                let gpu_device = GpuDevice {
                    id: gpu_idx.to_string(),
                    vendor: "Apple".to_string(),
                    model: chipset_model,
                    memory_bytes: vram_bytes,
                    pci_bus: "integrated".to_string(),
                    driver_version: "Metal".to_string(),
                    cuda_version: "N/A".to_string(),
                    attributes,
                };
                devices.push(gpu_device);
                gpu_idx += 1;
            }
        }

        Ok(devices)
    }

    fn get_utilization(&self, device_id: &str) -> Result<GpuUsage> {
        // Apple Metal does not expose per-process GPU utilization
        Ok(GpuUsage {
            device_id: device_id.to_string(),
            utilization_pct: 0,
            memory_used_bytes: 0,
            temperature_c: 0,
        })
    }
}

/// Factory function to create the appropriate GPU discovery backend for this platform
pub fn create_gpu_discovery() -> Option<Box<dyn GpuDiscovery + Send + Sync>> {
    #[cfg(target_os = "linux")]
    {
        Some(Box::new(NvidiaGpuDiscovery::new()))
    }

    #[cfg(target_os = "macos")]
    {
        Some(Box::new(AppleMetalGpuDiscovery::new()))
    }

    #[cfg(target_os = "windows")]
    {
        Some(Box::new(NvidiaGpuDiscovery::new()))
    }

    #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
    {
        None
    }
}

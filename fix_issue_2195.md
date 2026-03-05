# Pull Request: Add Configuration Option for Default Nimby Lock in rqd

## Summary

This PR introduces a new configuration option in `rqd.yaml` to enable the default Nimby Lock on startup, aligning with the requested enhancement. When specified, this option will mark a host as nimby_locked right away, without waiting for user interaction. This feature is particularly useful for scenarios where a machine should be locked by default to execute local rendering without processing external jobs.

## Implementation Details

1. **Configuration Update:**
   Added a new configuration option named `default_nimby_lock` to `rqd.yaml`. When set to `true`, the machine will start in a nimby locked state.

2. **Code Enhancement:**
   Modified the startup sequence to read the `default_nimby_lock` configuration and apply the nimby lock if enabled.

3. **Unit Tests:**
   Added unit tests to ensure that the configuration is parsed correctly and the nimby lock is set as expected during startup.

### Code Implementation

```rust
// config.rs

use serde::Deserialize;
use std::fs;

#[derive(Debug, Deserialize)]
pub struct RqdConfig {
    pub default_nimby_lock: Option<bool>,
}

impl RqdConfig {
    pub fn load_from_file(file_path: &str) -> Self {
        let config_content = fs::read_to_string(file_path).expect("Failed to read config file");
        toml::from_str(&config_content).expect("Invalid config format")
    }
}

// nimby.rs

pub struct Nimby {
    locked: bool,
}

impl Nimby {
    
    pub fn new(config: &RqdConfig) -> Self {
        let locked = config.default_nimby_lock.unwrap_or(false);
        Nimby { locked }
    }

    pub fn is_locked(&self) -> bool {
        self.locked
    }

    pub fn set_lock(&mut self, lock: bool) {
        self.locked = lock;
    }

    pub fn start(&self) {
        if self.locked {
            println!("Nimby is locked by default from configuration");
        } else {
            println!("Nimby is not locked by default");
        }
    }
}

// main.rs

mod config;
mod nimby;

fn main() {
    let config = config::RqdConfig::load_from_file("rqd.yaml");
    let nimby = nimby::Nimby::new(&config);
    nimby.start();
}

```

### Test Cases

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_nimby_lock_enabled() {
        let config_content = r#"
            default_nimby_lock = true
        "#;
        let config: RqdConfig = toml::from_str(config_content).unwrap();
        let nimby = Nimby::new(&config);

        assert!(nimby.is_locked());
    }

    #[test]
    fn default_nimby_lock_disabled() {
        let config_content = r#"
            default_nimby_lock = false
        "#;
        let config: RqdConfig = toml::from_str(config_content).unwrap();
        let nimby = Nimby::new(&config);

        assert!(!nimby.is_locked());
    }

    #[test]
    fn default_nimby_lock_unspecified() {
        let config_content = r#""#;
        let config: RqdConfig = toml::from_str(config_content).unwrap();
        let nimby = Nimby::new(&config);

        assert!(!nimby.is_locked());
    }
}
```

## Conclusion

This PR effectively introduces a configuration option to default a host to nimby locked upon startup. This change is targeted to enhance workflow flexibility and control for environments where machines should be locked by default. The added test cases validate the new configuration option's behavior and ensure backward compatibility when the configuration is not specified.
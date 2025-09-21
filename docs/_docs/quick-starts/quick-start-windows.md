---
layout: default
title: Quick start for Windows
nav_order: 5
parent: Quick Starts
---

# Quick start for Windows

### This quick start guide covers setting up an OpenCue deployment on Windows using Docker and docker-compose

---

## Prerequisites

- Windows 10/11 with WSL2 enabled
- Docker Desktop for Windows
- Git for Windows
- Python 3.6+ (for CueGUI)

## Setup Steps

### 1. Enable WSL2

If you haven't already enabled WSL2:

1. Open PowerShell as Administrator
2. Run:
   ```powershell
   wsl --install
   ```
3. Restart your computer

### 2. Install Docker Desktop

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. Install and ensure WSL2 backend is enabled
3. Start Docker Desktop

### 3. Clone the OpenCue repository

Open PowerShell or Command Prompt:

```bash
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue
```

### 4. Start OpenCue services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Cuebot server
- RQD (on the local machine)

### 5. Verify services are running

```bash
docker-compose ps
```

You should see all services in "Up" state.

### 6. Install Python dependencies

```bash
pip install pycue cuegui
```

### 7. Configure environment

Set the Cuebot host:

```bash
set CUEBOT_HOSTS=localhost
```

Or in PowerShell:
```powershell
$env:CUEBOT_HOSTS = "localhost"
```

### 8. Launch CueGUI

```bash
cuegui
```

## Testing the Setup

1. In CueGUI, you should see your local machine listed as a host
2. Submit a test job using CueSubmit:
   ```bash
   cuesubmit
   ```

## Troubleshooting

### Docker not starting
- Ensure virtualization is enabled in BIOS
- Check that WSL2 is properly installed
- Restart Docker Desktop

### CueGUI connection issues
- Verify CUEBOT_HOSTS is set correctly
- Check firewall settings for port 8443
- Ensure Cuebot container is running

### Performance issues
- Allocate more resources to Docker Desktop in Settings
- Use WSL2 backend for better performance

## Next Steps

- [Installing CueSubmit](../getting-started/installing-cuesubmit.md)
- [Submitting Jobs](../user-guides/submitting-jobs.md)
- [Configuring RQD](../other-guides/customizing-rqd.md)

For more detailed instructions, see the component-specific installation guides.
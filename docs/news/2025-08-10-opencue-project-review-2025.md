---
layout: default
title: "August 10, 2025: OpenCue Project Review 2025"
parent: News
nav_order: 1
---

# OpenCue Project Review 2025

### OpenCue Virtual Town Hall Series

#### August 10, 2025

---

Thanks to everyone who joined us for the OpenCue Virtual Town Hall 2025!

The Technical Steering Committee presented a comprehensive overview of OpenCue's progress, community growth, and exciting roadmap ahead. The presentation showcased major achievements, new features, and strategic initiatives for the coming year.

<div style="text-align: center; margin: 30px 0;">
  <iframe width="560" height="315" src="https://www.youtube.com/embed/GG7F0UM8T1Q" title="OpenCue Virtual Town Hall 2025" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
</div>

## About OpenCue

OpenCue is an open-source render farm management system that distributes workloads from artists across a cluster of computers. It has been used at Sony Pictures Imageworks, rendering all movies and animations since 2019.

## Community Overview

- Active community with 30-40+ contributors from various industries
- Currently searching for new TSC members
- Average pull request merge time reduced from 3 months to 8 days
- 80% contributor retention rate
- 485% increase in pull requests contributions

## Major Announcements

### CueWeb Release
Official announcement and release of CueWeb, our new browser-based visual interface featuring:
- Modern login integration
- Comprehensive job monitoring
- Advanced filtering capabilities
- Intuitive user experience

### Rust RQD Release
The render node monitoring agent has been completely rewritten in Rust, delivering:
- **5x smaller** memory footprint
- **50% reduction** in CPU usage
- Zero memory leaks
- Enhanced performance and reliability

## Latest Features

### Containerized Jobs (Docker Support)
- Run frames in Docker environments
- Simplified dependency management
- Execute legacy jobs on modern operating systems
- Improved job isolation and security

### Grafana Loki Integration
- Log aggregation and analysis
- Advanced querying capabilities
- Real-time charting and visualization
- Intelligent alerting system

### OpenCue Pip Packages Released
Installation simplified with official pip packages:

```bash
pip install opencue-proto opencue-pycue opencue-pyoutline opencue-rqd opencue-cueadmin opencue-cueman opencue-cuesubmit opencue-cuegui
```

- [opencue-proto](https://pypi.org/project/opencue-proto/)
  - `pip install opencue-proto`
- [opencue-pycue](https://pypi.org/project/opencue-pycue/)
  - `pip install opencue-pycue`
- [opencue-pyoutline](https://pypi.org/project/opencue-pyoutline/)
  - `pip install opencue-pyoutline`
- [opencue-rqd](https://pypi.org/project/opencue-rqd/)
  - `pip install opencue-rqd`
- [opencue-cueadmin](https://pypi.org/project/opencue-cueadmin/)
  - `pip install opencue-cueadmin`
- [opencue-cueman](https://pypi.org/project/opencue-cueman/)
  - `pip install opencue-cueman`
- [opencue-cuesubmit](https://pypi.org/project/opencue-cuesubmit/)
  - `pip install opencue-cuesubmit`
- [opencue-cuegui](https://pypi.org/project/opencue-cuegui/)
  - `pip install opencue-cuegui`

**Note:** Cuebot, Opencue REST Gateway, and CueWeb are deployed using Docker. For more information, see the Opencue's docker compose file (PostgreSQL, Cuebot, Flyway, RQD, OpenCue REST Gateway, and CueWeb): [docker-compose.yml](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/docker-compose.yml). 

#### Getting Started
- [Using the OpenCue Sandbox for Testing](https://docs.opencue.io/docs/developer-guide/sandbox-testing/)
- [Quick starts](https://docs.opencue.io/docs/quick-starts)
- [Getting Started](https://docs.opencue.io/docs/getting-started)

### New Documentation Website
Comprehensive documentation now available at [https://docs.opencue.io/](https://docs.opencue.io/) featuring:
- Video tutorials
- User guides
- API documentation
- Best practices

## Upcoming Features

### Distributed Booking
- Addresses database bottlenecks for large-scale render farms
- Enhanced scalability for enterprise deployments
- Improved job distribution efficiency

### Farm Auto-scaling
- Native autoscaling capabilities
- Automatic resource management based on queue pressure
- Cloud infrastructure optimization
- Cost-effective resource utilization

## Rust RQD Migration Timeline: 2025-2026
The complete migration to Rust RQD is planned for completion by 2026, ensuring a smooth transition for all users while maintaining backward compatibility.

## Get Involved

The OpenCue TSC is actively seeking new members! Join our vibrant community to:
- Contribute to cutting-edge render farm technology
- Collaborate with industry professionals
- Shape the future of OpenCue
- Share your expertise and learn from others

Stay connected with the OpenCue community for more updates as we continue to innovate and evolve the platform with your support!

[Our slides from the presentation are now available online](https://drive.google.com/file/d/1K9RQj9ewKgbuXlnVSnA5So47-6L1NnB2/view?usp=sharing)

---

[Watch the full presentation](https://www.youtube.com/watch?v=GG7F0UM8T1Q) | [Visit our GitHub](https://github.com/AcademySoftwareFoundation/OpenCue) | [Join the discussion](https://lists.aswf.io/g/opencue-dev)
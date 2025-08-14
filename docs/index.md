---
layout: home
title: <i class='fas fa-home'></i>&nbsp;Home
nav_order: 1
description: "OpenCue is an open source render management system for visual effects and animation."
permalink: /
---

<div class="hero-section">
    <!-- Floating Particles Background -->
    <div class="hero-particles"></div>
    
    <div class="hero-content">
        <div class="hero-logo-card">
            <img src="{{ '/assets/images/opencue-icon-black.svg' | relative_url }}" alt="OpenCue Logo" class="hero-logo" />
        </div>
        
        <div class="hero-text">
            <h1 class="hero-title">OpenCue</h1>
            <p class="hero-subtitle">An open source render management system</p>
            <p class="hero-description">Scale your rendering pipeline with job scheduling, resource optimization, and integration across your production workflow</p>
        </div>
        
        <div class="hero-actions">
            <a href="{{ '/docs/getting-started' | relative_url }}" class="btn-hero btn-primary" aria-label="Get started with OpenCue">
                <i class="fas fa-play" aria-hidden="true"></i>
                Get Started
            </a>
            <a href="{{ '/docs/' | relative_url }}" class="btn-hero btn-secondary" aria-label="Browse documentation">
                <i class="fas fa-book" aria-hidden="true"></i>
                View Docs
            </a>
            <a href="https://github.com/AcademySoftwareFoundation/OpenCue" class="btn-hero btn-outline" target="_blank" rel="noopener noreferrer" aria-label="View source code on GitHub">
                <i class="fab fa-github" aria-hidden="true"></i>
                GitHub
            </a>
        </div>
    </div>
</div>

<!-- Video Demo Section -->
<section class="video-section" aria-labelledby="video-heading">
    <div class="video-container">
        <h2 id="video-heading" class="section-title">OpenCue is an Official ASWF project</h2>
        <div class="video-wrapper">
            <iframe 
                src="https://www.youtube-nocookie.com/embed/Bq_N6Jamiac" 
                title="OpenCue Overview Video"
                frameborder="0" 
                allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen
                loading="lazy">
            </iframe>
        </div>
    </div>
</section>

<!-- Production Scale Stats Bar -->
<div class="stats-bar">
    <div class="stats-container">
        <div class="stat-item">
            <div class="stat-icon">
                <i class="fa-solid fa-rocket" aria-hidden="true"></i>
            </div>
            <div class="stat-text">High-scale rendering</div>
            <div class="stat-label">OpenCue provides features to manage rendering jobs at high-scale</div>
        </div>
        <div class="stat-item">
            <div class="stat-icon">
                <i class="fa-solid fa-film" aria-hidden="true"></i>
            </div>
            <div class="stat-text">Built for visual effects and animation</div>
            <div class="stat-label">Sony Pictures Imageworks in-house render manager used on hundreds of films</div>
        </div>
        <div class="stat-item">
            <div class="stat-icon">
                <i class="fa-solid fa-server" aria-hidden="true"></i>
            </div>
            <div class="stat-text">Render at scale</div>
            <div class="stat-label">Highly-scalable architecture supporting numerous concurrent machines</div>
        </div>
        <div class="stat-item">
            <div class="stat-icon">
                <i class="fa-solid fa-cloud" aria-hidden="true"></i>
            </div>
            <div class="stat-text">Flexible deployment</div>
            <div class="stat-label">Support for multi facility, on-premise, cloud, and hybrid deployments</div>
        </div>
    </div>
</div>

<!-- Feature Cards Grid -->
<section class="features-section" aria-labelledby="features-heading">
    <div class="features-container">
        <h2 id="features-heading" class="section-title">Powerful Render Management</h2>
        <p class="section-subtitle">Built for the demands of modern visual effects and animation production</p>
        
        <div class="features-grid">
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-calendar-check" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">Intelligent Scheduling</h3>
                <p class="feature-description">Advanced algorithms distribute render jobs across compute resources for optimal performance and resource utilization.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-layer-group" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">Scalable Architecture</h3>
                <p class="feature-description">From small studios to major facilities - handles thousands of concurrent jobs with enterprise-grade reliability.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-laptop-code" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">Cross-Platform</h3>
                <p class="feature-description">Native support for Linux, macOS, and Windows environments with consistent performance across platforms.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fab fa-python" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">Python Integration</h3>
                <p class="feature-description">Comprehensive Python API enables custom integrations, automation scripts, and seamless pipeline workflows.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-chart-line" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">Real-time Monitoring</h3>
                <p class="feature-description">Web-based and desktop GUI interfaces provide live job tracking, resource monitoring, and detailed performance analytics.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-puzzle-piece" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">DCC Integrations</h3>
                <p class="feature-description">Ready-made plugins for Maya, Nuke, Blender and other industry-standard digital content creation tools.</p>
            </div>
        </div>
    </div>
</section>

<!-- History Section -->
<section class="features-section" aria-labelledby="history-heading">
    <div class="features-container">
        <h2 id="history-heading" class="section-title">OpenCue History</h2>
        <p class="section-subtitle">Decades of production-proven render management evolution</p>
        
        <div class="features-grid">
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-history" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">Early Foundations</h3>
                <p class="feature-description">Early internal tools and scripts supported the first large-scale rendering workflows at <a href="https://www.imageworks.com/" target="_blank" rel="noopener noreferrer">Sony Pictures Imageworks</a> (SPI).</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-code-branch" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">1992–2006: Cue1 and Cue2</h3>
                <p class="feature-description">The earliest generations of <a href="https://www.imageworks.com/" target="_blank" rel="noopener noreferrer">Sony Pictures Imageworks</a> (SPI)'s internal queueing and render management systems.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-rocket" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">2007–2018: Cue3</h3>
                <p class="feature-description">A major internal rewrite of Cue1 and Cue2 at <a href="https://www.imageworks.com/" target="_blank" rel="noopener noreferrer">Sony Pictures Imageworks</a> that powered high-throughput, feature-film rendering at SPI for over a decade.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-handshake" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">2019–2021: OpenCue Launch</h3>
                <p class="feature-description">The <a href="https://www.imageworks.com/" target="_blank" rel="noopener noreferrer">Sony Pictures Imageworks</a>'s Cue3 core code was open-sourced in collaboration with Google, becoming <strong>OpenCue</strong>.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-certificate" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">2021: ASWF Adoption</h3>
                <p class="feature-description">OpenCue became an <a href="https://www.aswf.io/projects/" target="_blank" rel="noopener noreferrer">official Academy Software Foundation project</a>.</p>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-trophy" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">2023: Academy Award</h3>
                <p class="feature-description">Matt Chambers received a Scientific and Technical Academy Award for pioneering <a href="https://www.imageworks.com/" target="_blank" rel="noopener noreferrer">Sony Pictures Imageworks</a>’ original Cue3 system, later adapted as the Plow system at another company. Cue3 was further enhanced and evolved into what is now known as OpenCue.</p>
            </div>

            <!-- Academy Award Video -->
            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
                <iframe
                    src="https://www.youtube-nocookie.com/embed/0IhqqNz6q6k"
                    title="Academy Sci-Tech Award — Matt Chambers (Cue3/OpenCue)"
                    frameborder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowfullscreen
                    style="position: absolute; top:0; left:0; width:100%; height:100%;">
                </iframe>
            </div>
            
            <div class="feature-card" tabindex="0">
                <div class="feature-icon">
                    <i class="fas fa-sync-alt" aria-hidden="true"></i>
                </div>
                <h3 class="feature-title">2024–2025: Full Alignment</h3>
                <p class="feature-description">OpenCue's codebase is fully migrated and synchronized with SPI's internal code, ensuring the open-source project reflects current production realities.</p>
            </div>
        </div>
    </div>
</section>

<!-- Documentation Hub -->
<section class="docs-section" aria-labelledby="docs-heading">
    <div class="docs-container">
        <h2 id="docs-heading" class="section-title">Documentation Hub</h2>
        <p class="section-subtitle">Everything you need to deploy, manage, and extend OpenCue</p>
        
        <div class="docs-grid">
            <div class="doc-card" onclick="location.href='{{ '/docs/quick-starts' | relative_url }}';" tabindex="0" role="button" aria-label="Quick starts guide">
                <div class="doc-icon">
                    <i class="fas fa-rocket" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Quick Starts</h3>
                <p class="doc-description">Get OpenCue running in minutes with our sandbox guides for Linux, macOS, and Windows.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/concepts' | relative_url }}';" tabindex="0" role="button" aria-label="Concepts guide">
                <div class="doc-icon">
                    <i class="fas fa-lightbulb" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Core Concepts</h3>
                <p class="doc-description">Understand OpenCue's architecture, components, and fundamental principles.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/getting-started' | relative_url }}';" tabindex="0" role="button" aria-label="Getting started guide">
                <div class="doc-icon">
                    <i class="fas fa-server" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Installation Guide</h3>
                <p class="doc-description">Production deployment instructions for system administrators and DevOps teams.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/user-guides' | relative_url }}';" tabindex="0" role="button" aria-label="User guides">
                <div class="doc-icon">
                    <i class="fas fa-users" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">User Guides</h3>
                <p class="doc-description">Day-to-day workflows for artists, supervisors, and production staff.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/other-guides' | relative_url }}';" tabindex="0" role="button" aria-label="Other guides">
                <div class="doc-icon">
                    <i class="fas fa-compass" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Other Guides</h3>
                <p class="doc-description">Additional resources and specialized guides for specific use cases and integrations.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/reference' | relative_url }}';" tabindex="0" role="button" aria-label="Reference documentation">
                <div class="doc-icon">
                    <i class="fas fa-code" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Reference</h3>
                <p class="doc-description">Reference guides for all users running OpenCue tools and interfaces.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/tutorials' | relative_url }}';" tabindex="0" role="button" aria-label="Tutorials">
                <div class="doc-icon">
                    <i class="fas fa-graduation-cap" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Tutorials</h3>
                <p class="doc-description">Step-by-step walkthroughs for common tasks and advanced workflows.</p>
            </div>
            
            <div class="doc-card" onclick="location.href='{{ '/docs/developer-guide/index/' | relative_url }}';" tabindex="0" role="button" aria-label="Developer guide">
                <div class="doc-icon">
                    <i class="fas fa-tools" aria-hidden="true"></i>
                </div>
                <h3 class="doc-title">Developer Guide</h3>
                <p class="doc-description">Technical documentation for developers contributing to OpenCue and building custom integrations.</p>
            </div>
        </div>
    </div>
</section>

<!-- Community Section -->
<section class="community-section" aria-labelledby="community-heading">
    <div class="community-wrapper">
        <h2 id="community-heading" class="section-title">Join the OpenCue Community</h2>
        <p class="section-subtitle">Be part of the future of render management</p>
        
        <div class="community-container">
            <div class="community-card">
                <div class="community-icon">
                    <img src="{{ '/assets/images/opencue-icon-black.svg' | relative_url }}" alt="Academy Software Foundation" class="aswf-logo" />
                </div>
                <h3 class="community-card-title">Academy Software Foundation</h3>
                <p class="community-card-description">Official ASWF project advancing open source entertainment technology.</p>
            </div>
            
            <div class="community-card">
                <div class="community-icon">
                    <span class="unicode-icon">🤝</span>
                </div>
                <h3 class="community-card-title">Open Source Collaboration</h3>
                <p class="community-card-description">Contribute code, fixes, and knowledge to shape VFX industry tools.</p>
            </div>
            
            <div class="community-card">
                <div class="community-icon">
                    <span class="unicode-icon">⭐</span>
                </div>
                <h3 class="community-card-title">Industry Standard</h3>
                <p class="community-card-description">Used by developers, artists, and studios worldwide.</p>
            </div>
            
            <div class="community-card">
                <div class="community-icon">
                    <span class="unicode-icon">🚀</span>
                </div>
                <h3 class="community-card-title">Active Development</h3>
                <p class="community-card-description">Regular releases with community-driven roadmap and features.</p>
            </div>
        </div>
        
        <div class="community-actions">
            <a href="https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/CONTRIBUTING.md" class="btn-community btn-primary" target="_blank" rel="noopener noreferrer" aria-label="View contributing guide">
                <i class="fas fa-hands-helping" aria-hidden="true"></i>
                Contributing Guide
            </a>
            <a href="https://academysoftwarefdn.slack.com/archives/CMFPXV39Q" class="btn-community btn-secondary" target="_blank" rel="noopener noreferrer" aria-label="Join Slack community">
                <i class="fab fa-slack" aria-hidden="true"></i>
                Join Slack
            </a>
            <a href="https://github.com/AcademySoftwareFoundation/OpenCue/issues" class="btn-community btn-outline" target="_blank" rel="noopener noreferrer" aria-label="Report issues on GitHub">
                <i class="fas fa-bug" aria-hidden="true"></i>
                Report Issues
            </a>
        </div>
    </div>
</section>

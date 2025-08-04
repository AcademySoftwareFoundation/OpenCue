# OpenCue Documentation

This directory contains the official documentation for OpenCue, built with Jekyll and the [Just the Docs](https://github.com/just-the-docs/just-the-docs) theme. The documentation features a professional design with comprehensive search functionality, versioned content, and dark mode support.

## Quick Start

### Prerequisites

- **Ruby 3.0+** and Bundler
- **Git** for version control
- **Text editor** (VS Code, Sublime, etc.)

### Development Setup

1. **Clone and navigate to docs:**
   ```bash
   cd docs
   ```

2. **Install dependencies:**
   ```bash
   bundle install
   ```

3. **Test the build:**
   ```bash
   .build.sh
   ```

4. **Start development server:**
   ```bash
   bundle exec jekyll serve --livereload
   ```

5. **Open in browser:** http://localhost:4000/OpenCue

## Documentation Structure

```
docs/
├── _config.yml              # Jekyll configuration with versioning
├── _includes/               # Custom includes and theme components
│   └── header_custom.html   # Custom styling and site header
├── _docs/                   # Main documentation content
│   ├── concepts/            # Core concepts and overview
│   ├── getting-started/     # Installation and setup guides
│   ├── quick-starts/        # Platform-specific quick starts
│   ├── user-guides/         # End-user documentation
│   ├── other-guides/        # Advanced configuration and guides
│   ├── reference/           # API and command reference
│   └── tutorials/           # Step-by-step tutorials and guides
├── _sass/                   # Custom SCSS styles
│   └── color_schemes/       # Custom color schemes
├── assets/                  # Static assets
│   ├── images/              # Documentation images and logos
│   ├── js/                  # JavaScript files
│   └── css/                 # Generated CSS files
├── _plugins/                # Jekyll plugins for search and functionality
├── build.sh                 # Automated build testing script
├── Gemfile                  # Ruby dependencies
└── index.md                 # Homepage
```

## Writing Documentation

### Front Matter Template

All documentation pages should include comprehensive front matter:

```yaml
---
title: "Your Page Title"
nav_order: 1                    # Controls order in navigation
parent: "Parent Section"        # Optional, for nested pages
layout: default
linkTitle: "Short Title"        # Optional, for navigation
date: 2025-07-30               # Last updated date
description: >
  Brief description for SEO and social media previews.
  Can span multiple lines for detailed descriptions.
---
```

### Markdown Features

The documentation supports advanced Markdown features:

- **Standard Markdown:** Headers, lists, emphasis, links
- **Code blocks** with syntax highlighting:
  ```python
  def hello_opencue():
      print("Welcome to OpenCue!")
  ```
- **Tables** with sorting and styling
- **Callout boxes** for warnings and notes:
  ```markdown
  > **Note**
  > {: .callout .callout-info}
  > This is an informational callout.
  ```
- **Images** with proper baseurl support
- **Internal links** using Jekyll syntax

### Adding Images

1. **Place images** in `assets/images/`
2. **Reference with proper baseurl:**
   ```markdown
   ![Alt text](/OpenCue/assets/images/your-image.png)
   ```
3. **Use descriptive alt text** for accessibility

### Navigation Structure

**Documentation Collection** (`_docs/`):
- **Quick starts:** Try OpenCue in the sandbox environment on different operating systems
- **Concepts:** Conceptual guides for all users to introduce OpenCue
- **OpenCue getting started guide:** Guides for system admins deploying OpenCue components and installing dependencies
- **User guides:** Guides for artists and end-users completing common OpenCue user tasks
- **Other guides:** Guides for system admins and technical Production Services and Resources (PSR) teams completing common tasks related to managing, supporting, and troubleshooting OpenCue
- **Reference:** Reference guides for all users running OpenCue tools and interfaces
- **Tutorials:** Step-by-step learning guides and workflows
- **News:** Latest news, updates, and community announcements about OpenCue development and events
- **Releases:** OpenCue release announcements and changelogs

**Navigation Best Practices:**
- Use `nav_order` to control page ordering
- Use `parent` for hierarchical navigation
- Keep navigation depth to maximum 3 levels
- Use descriptive titles for better UX

## Dark Mode Support

### Features

- **Automatic theme detection** based on system preferences
- **Manual theme toggle** with persistent preference storage
- **Smooth transitions** between light and dark themes
- **Comprehensive styling** for all UI elements in both themes
- **Theme toggle button** with intuitive sun/moon icons (🌚/☀️)

### Implementation Details

The dark mode implementation includes:
- Custom dark color scheme in `_sass/color_schemes/opencue-dark.scss`
- Theme toggle functionality in `_includes/aux-nav.html`
- Theme persistence via localStorage in `_includes/header_custom.html`
- Professional dark gray design system with proper contrast ratios
- Enhanced button styling and auxiliary navigation layout

## Search Functionality

### Features

- **Client-side search** using [Lunr.js](https://lunrjs.com/)
- **Real-time results** as you type
- **Content indexing** of all documentation pages
- **Search highlighting** in results
- **Keyboard navigation** support
- **Keyboard shortcuts**: `Ctrl+K` (Windows/Linux) or `⌘+K` (Mac) to focus search
- **Visual shortcut indicators** displayed in the search box

### Search Configuration

Search settings in `_config.yml`:
```yaml
# Enable search
search_enabled: true
search:
  # Split pages into sections that can be searched individually
  heading_level: 2
  # Maximum search results
  previews: 3
  preview_words_before: 5
  preview_words_after: 10
  tokenizer_separator: /[\s\-/]+/
  # Display the relative url in search results
  rel_url: true
  # Enable or disable the search button that appears in the bottom right corner of every page
  button: true
```

## Testing and Validation

### Automated Testing

Use the comprehensive test script:

```bash
cd docs/
.build.sh
```

**Features:**
- Prerequisites validation
- Dependency installation
- Jekyll build with verbose output
- Critical file verification
- Image path validation
- Build statistics and size reporting
- Helpful testing suggestions

**Steps to run the script:**
- `cd docs/`
- `./build.sh` = Build validation and testing
- `bundle exec jekyll serve --livereload` = Local development server with live reload

### Manual compile and serve documentation:

Use the following commands to build and serve the documentation locally:

```bash
bundle exec jekyll build
bundle exec jekyll serve --livereload
```

Note: The `--livereload` flag in the command above enables live reloading, which automatically refreshes the page in 
your browser when changes are made to the documentation files.

### Manual Testing Checklist

- [ ] **Homepage loads** without errors
- [ ] **Navigation works** across all sections
- [ ] **Search functionality** returns relevant results
- [ ] **Images display** correctly with proper paths
- [ ] **Mobile responsiveness** on different screen sizes
  - On Google Chrome: Press **Ctrl+Shift+I** (or **Cmd+Option+I** on Mac) to open DevTools, then press **Ctrl+Shift+M** (or **Cmd+Shift+M** on Mac) to toggle mobile view and test responsiveness.
- [ ] **Link validation** - all internal/external links work

### Validation Tools

```bash
cd docs/

# Link checking
bundle exec jekyll build && find _site -name "*.html" -exec grep -l "href.*#" {} \;

# Build size analysis
du -sh _site
```

## Deployment

### GitHub Pages Deployment

Documentation is automatically deployed via GitHub Actions:

1. **Trigger:** Push to `master` branch
2. **Workflow:** `.github/workflows/docs.yml`
3. **Build environment:** Ubuntu with Ruby 3.x
4. **Deployment target:** GitHub Pages
5. **URL:** `https://academysoftwarefoundation.github.io/OpenCue` (will be changed to `https://opencue.io` in the future)

### Build Process

1. Install Ruby dependencies with Bundler
2. Run Jekyll build with production settings
3. Generate search index and optimized assets
4. Deploy to GitHub Pages with proper baseurl
5. Invalidate CDN cache for immediate updates

### Environment Variables

Key configuration for deployment:
```yaml
# _config.yml
baseurl: "/OpenCue"                                    # GitHub Pages path
url: "https://academysoftwarefoundation.github.io"    # Base domain
```

## Contributing

### Documentation Guidelines

1. **Follow style guide:** Consistent tone and formatting
2. **Test locally:** Use `./build.sh` before submitting
3. **Check links:** Ensure all references are valid
4. **Optimize images:** Compress images for web use
5. **Update navigation:** Maintain logical page hierarchy

### Submission Process

1. **Fork repository** and create feature branch
2. **Make changes** following documentation standards
3. **Test thoroughly** using provided scripts
4. **Submit pull request** with clear description
5. **Address feedback** from maintainers

### Content Standards

- **Clarity:** Write for technical and non-technical audiences
- **Accuracy:** Keep information current and correct
- **Completeness:** Include necessary context and examples
- **Accessibility:** Use proper headings and alt text
- **SEO:** Include meta descriptions and structured content

## Support and Resources

- **Main Repository:** [OpenCue on GitHub](https://github.com/AcademySoftwareFoundation/OpenCue)
- **Issue Tracking:** [GitHub Issues](https://github.com/AcademySoftwareFoundation/OpenCue/issues)
- **Community:** [OpenCue Slack](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q)
- **Jekyll Documentation:** [Jekyll Docs](https://jekyllrb.com/docs/)
- **Just the Docs Theme:** [Theme Documentation](https://just-the-docs.github.io/just-the-docs/)

## Troubleshooting

### Common Issues

**Build fails with dependency errors:**
```bash
bundle clean --force
bundle install
```


**Images not displaying:**
- Ensure proper baseurl (`/OpenCue/assets/images/`)
- Check file paths and case sensitivity
- Verify images exist in `assets/images/`

**Search not working:**
- Check that `search_enabled: true` in `_config.yml`
- Verify search data is generated in `_site/assets/js/`
- Test with clean browser session

### Getting Help

1. Check existing [GitHub Issues](https://github.com/AcademySoftwareFoundation/OpenCue/issues)
2. Run `./build.sh` for diagnostic information
3. Join the [OpenCue Slack](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q) for community support
4. Create detailed issue with error logs and steps to reproduce
# OpenCue Documentation

This directory contains the official documentation for OpenCue, built with Jekyll and the [Just the Docs](https://github.com/just-the-docs/just-the-docs) theme. The documentation features a professional design with comprehensive search functionality, versioned content, and dark mode support.

## Quick Start

### Option 1: Docker Setup (Recommended)

Build and serve documentation using Docker without installing Ruby locally:

```bash
cd docs/

# Build documentation
./docker-build.sh build

# Or serve with live reload
./docker-build.sh serve
```

See [DOCKER.md](DOCKER.md) for complete Docker setup documentation.

### Option 2: Local Setup

#### Prerequisites

- **Ruby 3.0+** and Bundler
- **Git** for version control
- **Text editor** (VS Code, Sublime, etc.)

#### Development Setup

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

5. **Open in browser:** http://localhost:4000/

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
│   ├── tutorials/           # Step-by-step tutorials and guides
│   └── developer-guide/     # Contributor and development guides
├── _news/                   # News entries, ordered by the date in the filename
├── _releases/               # Release announcements, ordered by their `date` front matter
├── _sass/                   # Custom SCSS styles
│   └── color_schemes/       # Custom color schemes
├── assets/                  # Static assets
│   ├── images/              # Documentation images and logos
│   ├── js/                  # JavaScript files
│   └── css/                 # Generated CSS files
├── _plugins/                # Jekyll plugins for search and functionality
├── build.sh                 # Automated build testing script
├── docker-build.sh          # Docker build helper script
├── Dockerfile               # Docker image for building docs
├── docker-compose.yml       # Docker Compose configuration
├── .dockerignore            # Docker build exclusions
├── Makefile                 # Make-based Docker build commands
├── DOCKER.md                # Docker setup documentation
├── validate_nav.py          # Navigation front matter validation (runs in build.sh and CI)
├── Gemfile                  # Ruby dependencies
├── news.md                  # News listing page
├── releases.md              # Releases listing page
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
   ![Alt text]({{ '/assets/images/your-image.png' | relative_url }})
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

## Navigation Order Management

`nav_order` is sorted **within each sibling group** -- pages that share the same `parent` and
`grand_parent`. It is never compared across sections, so the numbers in one section are
completely independent of every other section.

That gives two rules, and no scripts.

### Rule 1: number within your section, in steps of ten

Every sibling group starts at 10 and counts up by 10:

```
_docs/quick-starts/index.md              nav_order: 20   (top level)
_docs/quick-starts/quick-start-linux.md  nav_order: 10   (inside Quick Starts)
_docs/quick-starts/quick-start-mac.md    nav_order: 20
_docs/quick-starts/quick-start-windows.md nav_order: 30
```

To insert a page between macOS and Windows, give it `nav_order: 25` and change nothing else.
The gaps absorb nine insertions between any two pages before a section needs renumbering, and
that renumbering only ever touches the one section.

Two sibling pages must never share a `nav_order`. just-the-docs renders ties in an
unspecified order that can change between builds.

### Rule 2: dated content is ordered by its date, never by nav_order

News entries and release announcements are Jekyll collections sorted by date. They carry no
`nav_order` and no `parent`.

- **News** (`_news/`): name the file `YYYY-MM-DD-slug.md`. Jekyll reads the date from the
  filename, so the front matter needs nothing but `title`.
- **Releases** (`_releases/`): filenames are named after the version, so add
  `date: YYYY-MM-DD` to the front matter.

Adding a news post or a release means adding exactly one file. Nothing else changes.

### Validating

`validate_nav.py` enforces both rules and runs in `build.sh` and in CI:

```bash
cd docs
python3 validate_nav.py
```

It reports:

- duplicate `nav_order` values within a sibling group
- a `parent` that matches no page title, or whose target is missing `has_children: true`
- a `grand_parent` that is not the parent of the named `parent`
- `nav_order` or `parent` on a news or release entry
- a news file that is not named `YYYY-MM-DD-slug.md`, or a release without a `date`
- a page whose directory disagrees with the section it renders under (warning)

### Adding a new document

1. Create the file in the directory of the section it belongs to.
2. Set `title`, `parent` (the section index page's `title`), and a `nav_order` that fits
   between its neighbours.
3. Run `python3 validate_nav.py`.

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
5. **URL:** `https://docs.opencue.io` (redirected from `https://academysoftwarefoundation.github.io/OpenCue`)

### Deploying Documentation in Your Fork

For developers contributing to the OpenCue project who want to validate the OpenCue documentation in their fork of https://github.com/AcademySoftwareFoundation/OpenCue, follow these steps:

1. **Enable GitHub Pages in your fork:**
   - Go to Settings -> Pages
   - In Build and deployment -> Source, select GitHub Actions

2. **Configure Actions permissions:**
   - Go to Settings -> Actions -> General
   - Under Actions permissions, select "Allow all actions and reusable workflows"
   - Under Workflow permissions, select "Read and write permissions"

3. **Trigger the documentation deployment:**
   - Go to the Actions tab
   - Find the "Deploy Documentation" workflow and either re-run it or manually trigger it to publish your docs
   - Your documentation will be available at `https://[your-username].github.io/OpenCue`
   - Note: In your fork, you may need to update `baseurl` in `_config.yml` to `/OpenCue` for GitHub Pages

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
baseurl: ""                                    # Empty for root domain hosting
url: "https://docs.opencue.io"                # Production domain
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
- Ensure proper baseurl usage (`{{ '/assets/images/' | relative_url }}`)
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

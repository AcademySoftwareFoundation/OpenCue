# Docker Setup for OpenCue Documentation

This directory contains a Docker-based setup for building and serving OpenCue documentation without requiring a local Ruby installation.

## Prerequisites

- Docker (version 20.10 or later)
- Docker Compose (version 2.0 or later)

## Quick Start

### Build Documentation

Build the documentation once:

```bash
cd docs/
docker compose --profile build up
```

The built site will be available in the `_site/` directory.

### Serve Documentation Locally

Start a local development server with live reload:

```bash
cd docs/
docker compose --profile serve up
```

Then open http://localhost:4000 in your browser. Changes to documentation files will automatically trigger a rebuild.

### Using the Helper Script

For convenience, use the provided helper script:

```bash
# Build documentation
./docker-build.sh build

# Serve with live reload
./docker-build.sh serve

# Clean build artifacts
./docker-build.sh clean

# Show help
./docker-build.sh help
```

## Docker Compose Profiles

The setup includes three profiles for different use cases:

### 1. Build Profile (`build`)

Builds the documentation once and exits.

```bash
docker compose --profile build up
```

**Use case:** One-time builds, CI/CD pipelines, generating static output

### 2. Serve Profile (`serve`)

Starts a development server with live reload.

```bash
docker compose --profile serve up
```

**Use case:** Local development, testing changes in real-time

**Features:**
- Live reload on file changes
- Accessible at http://localhost:4000
- Force polling for file system compatibility

### 3. CI Profile (`ci`)

Builds without volume mounts for clean CI/CD environments.

```bash
docker compose --profile ci up
```

**Use case:** Continuous integration, automated builds

## Docker Commands Reference

### Building the Docker Image

```bash
# Build the image
docker compose build

# Build with no cache
docker compose build --no-cache
```

### Running Containers

```bash
# Build documentation (one-time)
docker compose --profile build up

# Serve documentation (development)
docker compose --profile serve up

# Run in detached mode
docker compose --profile serve up -d

# Stop running containers
docker compose down
```

### Accessing the Container

```bash
# Execute commands in running container
docker compose exec docs-serve bash

# Run one-off commands
docker compose run --rm docs-build bundle exec jekyll --version
```

### Cleaning Up

```bash
# Stop and remove containers
docker compose down

# Remove volumes
docker compose down -v

# Remove images
docker compose down --rmi all

# Clean build output
rm -rf _site .jekyll-cache
```

## Volume Management

The setup uses Docker volumes to persist Ruby gems and improve build performance:

- **docs-bundle**: Caches installed Ruby gems
- **Source mount**: Maps local `docs/` directory to `/docs` in container

### Benefits

- Faster subsequent builds (gems are cached)
- Changes to local files immediately reflected in container
- No need to rebuild image for documentation changes

### Clearing Cache

```bash
# Remove bundle cache
docker volume rm docs_docs-bundle

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
```

## Troubleshooting

### Port 4000 Already in Use

If port 4000 is already in use:

```bash
# Find process using port 4000
lsof -i :4000

# Kill the process
kill -9 <PID>

# Or use a different port
docker compose --profile serve run --rm -p 4001:4000 docs-serve
```

### Permission Issues

If you encounter permission issues with generated files:

```bash
# Fix ownership of generated files
sudo chown -R $USER:$USER _site .jekyll-cache
```

### Build Failures

If the build fails:

```bash
# Check logs
docker compose logs

# Rebuild without cache
docker compose build --no-cache

# Verify Gemfile.lock
rm Gemfile.lock
docker compose --profile build up
```

### Live Reload Not Working

If live reload doesn't work:

- Ensure you're using `--force_polling` flag (already included)
- Check browser console for WebSocket errors
- Try clearing browser cache
- Verify port 35729 (LiveReload port) is not blocked

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Documentation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build documentation with Docker
        run: |
          cd docs
          docker compose --profile ci up --abort-on-container-exit
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: documentation
          path: docs/_site/
```

### GitLab CI Example

```yaml
build-docs:
  image: docker:latest
  services:
    - docker:dind
  script:
    - cd docs
    - docker compose --profile ci up --abort-on-container-exit
  artifacts:
    paths:
      - docs/_site/
```

## Advanced Usage

### Custom Jekyll Commands

Run custom Jekyll commands:

```bash
# Check Jekyll version
docker compose run --rm docs-build bundle exec jekyll --version

# Build with specific config
docker compose run --rm docs-build bundle exec jekyll build --config _config.yml,_config_dev.yml

# Run with drafts
docker compose run --rm docs-build bundle exec jekyll serve --drafts --host 0.0.0.0
```

### Debugging

Enable verbose output:

```bash
# Verbose build
docker compose run --rm docs-build bundle exec jekyll build --verbose --trace

# Check bundle environment
docker compose run --rm docs-build bundle env
```

### Multi-stage Builds

For production deployments, consider using a multi-stage Dockerfile:

```dockerfile
# Build stage
FROM ruby:3.2-alpine AS builder
WORKDIR /docs
COPY Gemfile* ./
RUN bundle install
COPY . .
RUN bundle exec jekyll build

# Serve stage
FROM nginx:alpine
COPY --from=builder /docs/_site /usr/share/nginx/html
```

## Performance Tips

1. **Use volume caching**: The setup already uses volumes for gem caching
2. **Incremental builds**: Use `--incremental` flag for faster rebuilds
3. **Limit file watching**: Exclude unnecessary directories in `_config.yml`
4. **Use BuildKit**: Enable Docker BuildKit for faster builds:
   ```bash
   export DOCKER_BUILDKIT=1
   ```

## Comparison with Local Setup

| Feature | Docker Setup | Local Setup |
|---------|--------------|-------------|
| Ruby installation | Not required | Required (3.0+) |
| Dependency management | Containerized | System-wide |
| Consistency | Guaranteed | Varies by system |
| Setup time | Fast (pull image) | Slower (install deps) |
| Isolation | Complete | Limited |
| Performance | Slight overhead | Native speed |

## Support

For issues or questions:

- **GitHub Issues**: https://github.com/AcademySoftwareFoundation/OpenCue/issues
- **Slack**: #opencue on ASWF Slack
- **Documentation**: https://docs.opencue.io

## Related Files

- `Dockerfile` - Docker image definition
- `docker-compose.yml` - Docker Compose configuration
- `docker-build.sh` - Helper script for common tasks
- `Gemfile` - Ruby dependencies
- `_config.yml` - Jekyll configuration

# Dockerfile for building OpenCue documentation
# This provides a containerized environment for building Jekyll-based docs
# without requiring local Ruby installation

FROM ruby:3.2-alpine

LABEL maintainer="OpenCue Team"
LABEL description="Docker image for building OpenCue documentation with Jekyll"

# Install build dependencies.
# No Node.js toolchain here on purpose: the only JS-adjacent gem in the bundle is
# jekyll-sass-converter, which compiles Sass through the sass-embedded gem's
# native Dart binary, so nothing in the docs build shells out to node or npm.
# Leaving them out keeps an unpatched Node runtime out of the image (the
# October 2026 releases fixed CVE-2026-111497 in the bundled Brotli decoder).
RUN apk add --no-cache \
    build-base \
    git \
    tzdata

# Set working directory
WORKDIR /docs

# Copy Gemfile and Gemfile.lock first for better caching
COPY Gemfile* ./

# Install Ruby dependencies
RUN bundle install

# Copy the rest of the documentation files
COPY . .

# Expose Jekyll default port
EXPOSE 4000

# Default command: build the documentation
CMD ["bundle", "exec", "jekyll", "build", "--verbose"]

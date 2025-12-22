# Dockerfile for building OpenCue documentation
# This provides a containerized environment for building Jekyll-based docs
# without requiring local Ruby installation

FROM ruby:3.2-alpine

LABEL maintainer="OpenCue Team"
LABEL description="Docker image for building OpenCue documentation with Jekyll"

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    git \
    nodejs \
    npm \
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

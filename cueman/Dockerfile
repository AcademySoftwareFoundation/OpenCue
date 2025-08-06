# OpenCue Cueman Docker Image
# Production-ready image for cueman command-line tool
FROM python:3.9.14-slim


# Set working directory
WORKDIR /opt/opencue

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip and setuptools
RUN python3 -m pip install --upgrade pip setuptools wheel

# Copy version and documentation from root
COPY VERSION.in ./
RUN test -e VERSION || echo "$(cat VERSION.in)" | tee VERSION

# Copy documentation and source code
COPY LICENSE ./
COPY cueman/README.md cueman/cueman_tutorial.md ./docs/
COPY cueman/ ./cueman/

# In production, install from PyPI:
# RUN python3 -m pip install opencue-cueman
# For development/demo, we would install from source but this requires
# the full OpenCue proto compilation which is complex for Docker builds.

# Create non-root user for security
RUN groupadd -r cueman && useradd -r -g cueman -s /bin/bash -d /opt/opencue cueman
RUN chown -R cueman:cueman /opt/opencue

# Switch to non-root user
USER cueman

# Set environment variables
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/usr/local/lib/python3.9/site-packages

# Default working directory for user operations
WORKDIR /opt/opencue

# In a production environment, the health check would test cueman:
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD cueman -h > /dev/null || exit 1

# Default command shows usage information
CMD ["sh", "-c", "echo 'OpenCue Cueman - CLI Job Management Tool' && echo 'Install with: pip install opencue-cueman' && echo 'Documentation available in /opt/opencue/docs/' && echo 'Source code available in /opt/opencue/cueman/'"]

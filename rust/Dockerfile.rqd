# Multi-stage Dockerfile for OpenCue Rust RQD

# Build stage
FROM rust:1.88-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    protobuf-compiler \
    libprotobuf-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /build

# Copy workspace files
COPY rust/Cargo.toml ./
COPY rust/Cargo.lock* ./

# Copy all crate directories
COPY rust/crates ./crates

# Remove symlink and copy proto files from repo root
RUN rm ./crates/opencue-proto/src/protos
COPY proto/src ./crates/opencue-proto/src/protos

# Build RQD in release mode
RUN cargo build --release -p rqd

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 -s /bin/bash rqd

# Create necessary directories
RUN mkdir -p /app/resources && chown -R rqd:rqd /app

WORKDIR /app

# Copy the built binary from builder stage
COPY --from=builder /build/target/release/openrqd /app/openrqd

# Copy resources
COPY --from=builder /build/crates/rqd/resources /app/resources

# RQD gRPC server
EXPOSE 8444

# Run RQD
ENTRYPOINT ["/app/openrqd"]
CMD []

# Build from project root
FROM rockylinux:9.3 as rocky-golang

WORKDIR /src/go
RUN dnf install -y 'dnf-command(config-manager)' && dnf config-manager --set-enabled crb

# WARN: Download do tarball and update file path accordingly
COPY rest_gateway/Go_1.22.2_Linux_ARM64.tar.gz golang.tar.gz

RUN tar -C /usr/local -xzf golang.tar.gz
ENV PATH="$PATH:/usr/local/go/bin"

# WARN: Uncoment if your environment requires a proxy
#ENV GOPROXY=artifactory.yourcompany.com/go-proxy
ENV GO111MODULE=on
ENV GOSUMDB=off

RUN go version

RUN rm -rf /src/go

FROM rocky-golang AS build

RUN dnf install -y \
    git \ 
    protobuf-compiler \ 
    && dnf clean all
WORKDIR /app
ENV PATH=$PATH:/root/go/bin:/opt/protobuf3/usr/bin/

# Copy all of the staged files (protos plus go source)
COPY ./proto /app/proto
COPY ./rest_gateway/opencue_gateway /app/opencue_gateway
# COPY ./lib /app/lib

 
WORKDIR /app/opencue_gateway
RUN go mod init opencue_gateway && go mod tidy

RUN go install \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2 \
    google.golang.org/protobuf/cmd/protoc-gen-go \
    google.golang.org/grpc/cmd/protoc-gen-go-grpc

# Generate go grpc code
RUN mkdir -p gen/go && \
    protoc -I ../proto/ \
    --go_out ./gen/go/ \
    --go_opt paths=source_relative \
    --go-grpc_out ./gen/go/ \
    --go-grpc_opt paths=source_relative \
    ../proto/*.proto

# Generate grpc-gateway handlers
RUN protoc -I ../proto/ --grpc-gateway_out ./gen/go \
    --grpc-gateway_opt paths=source_relative \
    --grpc-gateway_opt generate_unbound_methods=true \
    ../proto/*.proto

# Build project
RUN go build -o grpc_gateway main.go

FROM rockylinux:9.3
COPY --from=build /app/opencue_gateway/grpc_gateway /app/

EXPOSE 8448
ENTRYPOINT ["/app/grpc_gateway"]

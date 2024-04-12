package main
import (
	"context"
	"flag"
	"net/http"
	"os"
  
	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/grpclog"
  
	gw "opencue_gateway/gen/go"  // Update
  )

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func run() error {
	grpcServerEndpoint := getEnv("CUEBOT_ENDPOINT", "opencuetest01.your.test.server:8443")
	port := getEnv("REST_PORT", "8448")

	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Register gRPC server endpoint
	// Note: Make sure the gRPC server is running properly and accessible
	mux := runtime.NewServeMux()
	opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}
	
	// show.proto
	errShow := gw.RegisterShowInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errShow != nil {
		return errShow
	}

	errFrame := gw.RegisterFrameInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errFrame != nil {
		return errFrame
	}
	errGroup := gw.RegisterGroupInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errGroup != nil {
		return errGroup
	}
	errJob := gw.RegisterJobInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errJob != nil {
		return errJob
	}
	errLayer := gw.RegisterLayerInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errLayer != nil {
		return errLayer
	}

	// host.proto
	errDeed := gw.RegisterDeedInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errDeed != nil {
		return errDeed
	}
	errHost := gw.RegisterHostInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errHost != nil {
		return errHost
	}
	errOwner := gw.RegisterOwnerInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errOwner != nil {
		return errOwner
	}
	errProc := gw.RegisterProcInterfaceHandlerFromEndpoint(ctx, mux, grpcServerEndpoint, opts)
	if errProc != nil {
		return errProc
	}
	
	
	// Start HTTP server (and proxy calls to gRPC server endpoint)
	return http.ListenAndServe(":" + port, mux)
}

func main() {
	flag.Parse()

	if err := run(); err != nil {
		grpclog.Fatal(err)
	}
}
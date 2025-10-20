// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Package main implements the OpenCue REST Gateway server.
//
// The REST Gateway provides HTTP/REST endpoints for all OpenCue gRPC interfaces,
// enabling web applications and HTTP clients to interact with OpenCue without
// requiring gRPC clients. It uses the grpc-gateway framework to automatically
// translate HTTP requests to gRPC calls and responses back to JSON.
//
// Architecture:
//   - HTTP Server: Listens for incoming REST requests on port 8448 (default)
//   - JWT Middleware: Authenticates all requests using HMAC SHA256 tokens
//   - gRPC Gateway: Translates HTTP/JSON to gRPC and back
//   - Connection Pool: Manages connections to Cuebot gRPC server
//
// Required Environment Variables:
//   - CUEBOT_ENDPOINT: Cuebot gRPC server address (e.g., "localhost:8443")
//   - REST_PORT: HTTP server port (e.g., "8448")
//   - JWT_SECRET: Secret key for JWT token validation
//
// Example usage:
//
//	docker run -d \
//	  -e CUEBOT_ENDPOINT=cuebot:8443 \
//	  -e REST_PORT=8448 \
//	  -e JWT_SECRET=your-secret-key \
//	  -p 8448:8448 \
//	  opencue-rest-gateway
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/golang-jwt/jwt/v5"
	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/grpclog"

	gw "opencue_gateway/gen/go" // Generated protobuf code
)

// getEnv retrieves a required environment variable or exits if not found.
//
// This function ensures that all required configuration is present at startup,
// following the "fail fast" principle. If a required environment variable is
// missing, the application will exit immediately with a clear error message.
//
// Parameters:
//   - key: The environment variable name to retrieve
//
// Returns:
//   - The value of the environment variable
//
// Exits with error if the environment variable is not set.
func getEnv(key string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	log.Fatal(fmt.Sprintf("Error: required environment variable '%v' not found", key))
	return "" // Unreachable, but required for compilation
}

// validateJWTToken parses and validates a JWT token string using HMAC SHA256.
//
// This function performs cryptographic validation of the JWT token to ensure:
//   - The token is well-formed and parseable
//   - The signature is valid using the provided secret
//   - The signing algorithm is HMAC (HS256, HS384, or HS512)
//   - The token has not expired
//
// Parameters:
//   - tokenString: The JWT token to validate (without "Bearer " prefix)
//   - jwtSecret: The secret key used to sign the token
//
// Returns:
//   - *jwt.Token: The parsed and validated token object
//   - error: Validation error if the token is invalid, nil if valid
//
// Security Note:
//
//	This function explicitly checks that the signing method is HMAC to prevent
//	algorithm substitution attacks where an attacker might try to use "none"
//	or asymmetric algorithms.
func validateJWTToken(tokenString string, jwtSecret []byte) (*jwt.Token, error) {
	log.Println("Validating JWT token")
	return jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Ensure that the token's signing method is HMAC to prevent algorithm attacks
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			errorString := fmt.Sprintf("Unexpected signing method: %v", token.Header["alg"])
			log.Printf("%s", errorString)
			return nil, fmt.Errorf("%s", errorString)
		}
		log.Println("JWT signing method validated")
		return jwtSecret, nil
	})
}

// jwtMiddleware is an HTTP middleware that enforces JWT authentication on all requests.
//
// This middleware wraps HTTP handlers to require valid JWT authentication before
// processing any request. It implements the following security flow:
//
//  1. Extracts the Authorization header from the request
//  2. Validates the "Bearer" token format
//  3. Cryptographically verifies the JWT signature
//  4. Checks token expiration and validity
//  5. Returns 401 Unauthorized if any check fails
//  6. Passes the request to the next handler if authentication succeeds
//
// All REST Gateway endpoints are protected by this middleware - there are no
// public or unauthenticated endpoints.
//
// Parameters:
//   - next: The HTTP handler to call if authentication succeeds
//   - jwtSecret: The secret key for JWT validation
//
// Returns:
//   - http.Handler: The wrapped handler with JWT authentication
//
// Example Authorization Header:
//
//	Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
func jwtMiddleware(next http.Handler, jwtSecret []byte) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Extract and validate Authorization header
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			errorString := "Authorization header required"
			log.Printf("%s", errorString)
			http.Error(w, errorString, http.StatusUnauthorized)
			return
		}

		// Extract token from "Bearer <token>" format
		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
		token, err := validateJWTToken(tokenString, jwtSecret)
		if err != nil {
			errorString := fmt.Sprintf("Token validation error: %v", err)
			log.Printf("%s", errorString)
			http.Error(w, errorString, http.StatusUnauthorized)
			return
		}
		if !token.Valid {
			errorString := "Invalid token"
			log.Printf("%s", errorString)
			http.Error(w, errorString, http.StatusUnauthorized)
			return
		}

		log.Println("Token validated successfully; passing request to next handler")
		next.ServeHTTP(w, r)
	})
}

// run initializes and starts the REST Gateway server.
//
// This function orchestrates the complete server setup:
//  1. Loads configuration from environment variables
//  2. Creates gRPC-gateway multiplexer for HTTP-to-gRPC translation
//  3. Registers all OpenCue interface handlers
//  4. Wraps handlers with JWT authentication middleware
//  5. Starts the HTTP server
//
// The server will continue running until it receives a termination signal
// or encounters a fatal error.
//
// Returns:
//   - error: Server startup or runtime error, nil on normal shutdown
//
// Required Environment Variables:
//   - CUEBOT_ENDPOINT: Cuebot gRPC server address
//   - REST_PORT: HTTP listening port
//   - JWT_SECRET: Secret for JWT validation
func run() error {
	grpcServerEndpoint := getEnv("CUEBOT_ENDPOINT")
	port := getEnv("REST_PORT")
	jwtSecret := []byte(getEnv("JWT_SECRET"))

	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Initialize gRPC-gateway multiplexer for HTTP-to-gRPC translation
	mux := runtime.NewServeMux()

	// Configure gRPC connection options (using insecure for internal network)
	opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}

	// Register all gRPC interface handlers
	if err := registerGRPCHandlers(ctx, mux, grpcServerEndpoint, opts); err != nil {
		return fmt.Errorf("failed to register gRPC handlers: %w", err)
	}

	log.Println("All gRPC handlers registered successfully")

	// Create HTTP multiplexer and apply JWT authentication middleware
	httpMux := http.NewServeMux()
	httpMux.Handle("/", jwtMiddleware(mux, jwtSecret))

	log.Printf("Starting HTTP server on endpoint: %s, port %s", grpcServerEndpoint, port)

	// Start HTTP server and begin proxying requests to Cuebot
	return http.ListenAndServe(":"+port, httpMux)
}

// registerGRPCHandlers registers all OpenCue gRPC interface handlers with the gateway.
//
// This function registers REST endpoint handlers for all OpenCue interfaces,
// enabling complete API coverage including both core and management operations:
//
// Parameters:
//   - ctx: Context for handler registration
//   - mux: gRPC-gateway multiplexer to register handlers with
//   - grpcServerEndpoint: Cuebot gRPC server address
//   - opts: gRPC dial options for connection configuration
//
// Returns:
//   - error: Registration error if any handler fails, nil on success
func registerGRPCHandlers(ctx context.Context, mux *runtime.ServeMux, grpcServerEndpoint string, opts []grpc.DialOption) error {
	log.Println("Registering gRPC handlers")

	// Array of all handler registration functions
	// Each function registers REST endpoints for one OpenCue interface
	handlers := []func(context.Context, *runtime.ServeMux, string, []grpc.DialOption) error{
		// Core interfaces (original 10)
		gw.RegisterShowInterfaceHandlerFromEndpoint,
		gw.RegisterFrameInterfaceHandlerFromEndpoint,
		gw.RegisterGroupInterfaceHandlerFromEndpoint,
		gw.RegisterJobInterfaceHandlerFromEndpoint,
		gw.RegisterLayerInterfaceHandlerFromEndpoint,
		gw.RegisterDeedInterfaceHandlerFromEndpoint,
		gw.RegisterHostInterfaceHandlerFromEndpoint,
		gw.RegisterOwnerInterfaceHandlerFromEndpoint,
		gw.RegisterProcInterfaceHandlerFromEndpoint,
		gw.RegisterCommentInterfaceHandlerFromEndpoint,
		// Management interfaces
		gw.RegisterAllocationInterfaceHandlerFromEndpoint,
		gw.RegisterFacilityInterfaceHandlerFromEndpoint,
		gw.RegisterFilterInterfaceHandlerFromEndpoint,
		gw.RegisterActionInterfaceHandlerFromEndpoint,
		gw.RegisterMatcherInterfaceHandlerFromEndpoint,
		gw.RegisterDependInterfaceHandlerFromEndpoint,
		gw.RegisterSubscriptionInterfaceHandlerFromEndpoint,
		gw.RegisterLimitInterfaceHandlerFromEndpoint,
		gw.RegisterServiceInterfaceHandlerFromEndpoint,
		gw.RegisterServiceOverrideInterfaceHandlerFromEndpoint,
		gw.RegisterTaskInterfaceHandlerFromEndpoint,
	}

	// Register each handler, failing fast if any registration fails
	for _, handler := range handlers {
		if err := handler(ctx, mux, grpcServerEndpoint, opts); err != nil {
			log.Printf("Error registering gRPC handler: %v", err)
			return err
		}
	}
	log.Println("All gRPC handlers registered")
	return nil
}

// main is the entry point for the OpenCue REST Gateway server.
//
// This function:
//  1. Sets up logging to both stdout and file (/logs/opencue_gateway.log)
//  2. Parses command-line flags
//  3. Calls run() to start the server
//  4. Handles fatal errors and graceful shutdown
//
// The server runs indefinitely until terminated by signal or fatal error.
func main() {
	// Configure logging to write to both stdout and log file
	f, err := os.OpenFile("/logs/opencue_gateway.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	// MultiWriter sends logs to both stdout and file
	mw := io.MultiWriter(os.Stdout, f)
	log.SetOutput(mw)

	flag.Parse()
	log.Println("Starting main application")

	// Start the server (blocks until shutdown or error)
	if err := run(); err != nil {
		grpclog.Fatal(err)
	}
}

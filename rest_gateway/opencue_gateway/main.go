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
// Optional Environment Variables:
//   - SWAGGER_ENABLED: Serve the Swagger UI on /swagger/ (default "true").
//     The UI is not authenticated, so set this to "false" wherever the gateway
//     is reachable beyond a trusted network.
//   - SWAGGER_DIR: Directory holding the generated OpenAPI documents
//     (default "./gen/openapiv2")
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
	"encoding/json"
	"flag"
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"unicode"

	"github.com/golang-jwt/jwt/v5"
	"github.com/grpc-ecosystem/grpc-gateway/v2/runtime"
	swaggerfiles "github.com/swaggo/files/v2"
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
// All REST Gateway API endpoints are protected by this middleware. The only
// exception is the Swagger UI mounted under /swagger/, which is deliberately
// served without authentication so the API can be browsed; see
// registerSwaggerHandlers and the SWAGGER_ENABLED environment variable.
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

	// Configure gRPC connection options (using insecure for internal network).
	// Raise the max receive message size above gRPC's 4MB default so large list
	// responses (e.g. GetJobs on a busy production facility — tens of MB) aren't
	// rejected with "received message larger than max". Override via
	// GRPC_MAX_RECV_MSG_MB (megabytes).
	maxRecvMsgBytes := 256 * 1024 * 1024 // 256 MB default
	if v := os.Getenv("GRPC_MAX_RECV_MSG_MB"); v != "" {
		if mb, err := strconv.Atoi(v); err == nil && mb > 0 {
			maxRecvMsgBytes = mb * 1024 * 1024
		}
	}
	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(maxRecvMsgBytes)),
	}

	// Register all gRPC interface handlers
	if err := registerGRPCHandlers(ctx, mux, grpcServerEndpoint, opts); err != nil {
		return fmt.Errorf("failed to register gRPC handlers: %w", err)
	}

	log.Println("All gRPC handlers registered successfully")

	// Create HTTP multiplexer and mount routes
	httpMux := http.NewServeMux()

	// Swagger UI / OpenAPI handling.
	//
	// SECURITY: these routes are mounted *outside* jwtMiddleware so the API can be
	// browsed without a token. That publishes the complete API surface to anyone who
	// can reach the port, so deployments that expose the gateway beyond a trusted
	// network should set SWAGGER_ENABLED=false.
	registerSwaggerHandlers(httpMux)

	// Apply JWT authentication middleware to all other routes
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
		gw.RegisterDepartmentInterfaceHandlerFromEndpoint,
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

// swaggerSpecItem represents an entry in Swagger UI's top-bar selector.
type swaggerSpecItem struct {
	URL  string `json:"url"`
	Name string `json:"name"`
}

// swaggerUIAssets is the allow-list of files served from the embedded Swagger UI
// distribution. The dist also ships index.html and swagger-initializer.js, which
// point at https://petstore.swagger.io, plus ~7 MB of .map files; none of those
// belong on an unauthenticated route, so only what swaggerUITemplate references
// is exposed.
var swaggerUIAssets = map[string]bool{
	"swagger-ui.css":                  true,
	"swagger-ui-bundle.js":            true,
	"swagger-ui-standalone-preset.js": true,
}

// swaggerUITmpl is parsed once at startup rather than on every request.
var swaggerUITmpl = template.Must(template.New("swagger").Parse(swaggerUITemplate))

// swaggerEnabled reports whether the Swagger UI routes should be mounted.
//
// The UI is served without authentication, so operators need a way to switch it
// off. It defaults to enabled to preserve the documented behaviour; set
// SWAGGER_ENABLED to a false value ("false", "0", "no", "off") to disable it.
func swaggerEnabled() bool {
	v, ok := os.LookupEnv("SWAGGER_ENABLED")
	if !ok {
		return true
	}
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "false", "0", "no", "off":
		return false
	default:
		return true
	}
}

// swaggerDirectory returns the directory holding the generated OpenAPI specs.
func swaggerDirectory() string {
	if dir := os.Getenv("SWAGGER_DIR"); dir != "" {
		return dir
	}
	return "./gen/openapiv2"
}

// registerSwaggerHandlers mounts the Swagger UI routes on mux.
//
// Three routes are mounted, all of them unauthenticated:
//
//	/swagger/         - the generated Swagger UI page
//	/swagger/specs/   - the generated OpenAPI JSON documents
//	/swagger/assets/  - the embedded Swagger UI JavaScript and CSS
//
// Nothing is mounted when the UI is disabled or when the spec directory is
// missing, in which case /swagger/ falls through to the authenticated handler.
func registerSwaggerHandlers(mux *http.ServeMux) {
	if !swaggerEnabled() {
		log.Println("SWAGGER_ENABLED is false; not mounting /swagger/ handlers")
		return
	}

	swaggerDir := swaggerDirectory()
	info, err := os.Stat(swaggerDir)
	if err != nil || !info.IsDir() {
		log.Printf("Swagger directory %s not found; skipping /swagger/ handlers", swaggerDir)
		return
	}

	log.Printf("Serving Swagger UI / OpenAPI specs from %s on /swagger/ (no authentication required)", swaggerDir)

	// 1. Serve the allow-listed Swagger UI static assets (JS, CSS).
	assetServer := http.StripPrefix("/swagger/assets/", http.FileServer(http.FS(swaggerfiles.FS)))
	mux.HandleFunc("/swagger/assets/", func(w http.ResponseWriter, r *http.Request) {
		if !swaggerUIAssets[strings.TrimPrefix(r.URL.Path, "/swagger/assets/")] {
			http.NotFound(w, r)
			return
		}
		assetServer.ServeHTTP(w, r)
	})

	// 2. Serve the generated OpenAPI documents.
	mux.HandleFunc("/swagger/specs/", func(w http.ResponseWriter, r *http.Request) {
		serveSwaggerSpec(w, r, swaggerDir)
	})

	// 3. Serve the dynamically generated Swagger UI HTML page.
	mux.HandleFunc("/swagger/", func(w http.ResponseWriter, r *http.Request) {
		serveSwaggerUI(w, swaggerDir)
	})
}

// serveSwaggerSpec serves a single generated OpenAPI document from swaggerDir.
//
// Only plain ".json" file names directly inside swaggerDir are served. Requests
// for a nested path, a traversal sequence, or the directory itself return 404,
// which also keeps http.FileServer's directory listing off /swagger/specs/.
func serveSwaggerSpec(w http.ResponseWriter, r *http.Request, swaggerDir string) {
	name := strings.TrimPrefix(r.URL.Path, "/swagger/specs/")
	if name == "" || strings.Contains(name, "/") || !strings.HasSuffix(name, ".json") {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, filepath.Join(swaggerDir, filepath.Base(name)))
}

// titleCase upper-cases the first letter of each space-separated word in s.
//
// strings.Title is deprecated as of Go 1.18, and golang.org/x/text/cases would
// pull in a dependency for what is only cosmetic formatting of a file name.
func titleCase(s string) string {
	words := strings.Fields(s)
	for i, word := range words {
		runes := []rune(word)
		runes[0] = unicode.ToUpper(runes[0])
		words[i] = string(runes)
	}
	return strings.Join(words, " ")
}

// swaggerSpecs lists the OpenAPI documents available in swaggerDir, turning each
// file name into a display name for Swagger UI's definition selector.
func swaggerSpecs(swaggerDir string) ([]swaggerSpecItem, error) {
	entries, err := os.ReadDir(swaggerDir)
	if err != nil {
		return nil, err
	}

	var specs []swaggerSpecItem
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.HasSuffix(name, ".json") {
			continue
		}

		// "job.swagger.json" -> "Job Service"
		displayName := strings.TrimSuffix(name, ".json")
		displayName = strings.TrimSuffix(displayName, ".swagger")
		displayName = titleCase(strings.ReplaceAll(displayName, "_", " ")) + " Service"

		specs = append(specs, swaggerSpecItem{
			URL:  "/swagger/specs/" + name,
			Name: displayName,
		})
	}
	return specs, nil
}

// serveSwaggerUI renders the Swagger UI page for every spec found in swaggerDir.
func serveSwaggerUI(w http.ResponseWriter, swaggerDir string) {
	specs, err := swaggerSpecs(swaggerDir)
	if err != nil {
		log.Printf("Failed to read swagger directory %s: %v", swaggerDir, err)
		http.Error(w, "Failed to read swagger directory", http.StatusInternalServerError)
		return
	}

	// json.Marshal escapes <, > and & as <, > and &, so the result
	// is safe to embed in a <script> block as template.JS.
	specsJSON, err := json.Marshal(specs)
	if err != nil {
		log.Printf("Failed to encode swagger spec list: %v", err)
		http.Error(w, "Failed to encode specs", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := swaggerUITmpl.Execute(w, template.JS(specsJSON)); err != nil {
		// The header is already written, so this can only be logged.
		log.Printf("Failed to render Swagger UI page: %v", err)
	}
}

const swaggerUITemplate = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenCue REST API Documentation</title>
  <link rel="stylesheet" href="/swagger/assets/swagger-ui.css" />
  <style>
    body { margin: 0; padding: 0; background: #fafafa; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/swagger/assets/swagger-ui-bundle.js"></script>
  <script src="/swagger/assets/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        urls: {{ . }},
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout",
        requestInterceptor: (req) => {
          // Normalise the value from the Authorize dialog to "Bearer <token>".
          // authSelectors.authorized() returns an Immutable.Map, so the value has
          // to be read with getIn() rather than plain property access. window.ui
          // is guarded because this can fire before the assignment above returns.
          const auth = window.ui && window.ui.authSelectors.authorized();
          const token = auth && auth.getIn(["BearerAuth", "value"]);
          if (token) {
            req.headers["Authorization"] =
              token.startsWith("Bearer ") ? token : "Bearer " + token;
          }
          return req;
        },
        responseInterceptor: (res) => {
          // Inject security definition so the "Authorize" button always appears
          if (res.url.includes("/swagger/specs/")) {
            try {
              const spec = JSON.parse(res.text);
              if (!spec.securityDefinitions) {
                spec.securityDefinitions = {};
              }
              spec.securityDefinitions.BearerAuth = {
                type: "apiKey",
                name: "Authorization",
                in: "header",
                // Rendered as markdown, so angle-bracket placeholders would be
                // stripped as HTML tags.
                description: "Paste your JWT here. The 'Bearer ' prefix is optional and is added automatically."
              };
              spec.security = [{ BearerAuth: [] }];
              res.text = JSON.stringify(spec);
              res.data = JSON.stringify(spec);
            } catch (e) {
              console.error("Failed to inject BearerAuth into spec", e);
            }
          }
          return res;
        }
      });
    };
  </script>
</body>
</html>
`

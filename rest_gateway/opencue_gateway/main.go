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
  
	gw "opencue_gateway/gen/go"  // Update
  )

func getEnv(key string) string {
	// Return the value of the environment variable if it's found
	if value, ok := os.LookupEnv(key); ok {
		return value
	} else {
		// If the environment variable is not found, output an error and exit the program
		log.Fatal(fmt.Sprintf("Error: environment variable '%v' not found", key))
	}
	return ""
}

// Parse and validate the JWT token string
func validateJWTToken(tokenString string, jwtSecret []byte) (*jwt.Token, error) {
	log.Println("Validating JWT token")
	return jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Ensure that the token's signing method is HMAC
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			errorString := fmt.Sprintf("Unexpected signing method: %v", token.Header["alg"])
			log.Printf(errorString)
			return nil, fmt.Errorf(errorString)
		}
		log.Println("JWT signing method validated")
		// Return the secret key for validation
		return jwtSecret, nil
	})
}

// Middleware to handle token authorization
func jwtMiddleware(next http.Handler, jwtSecret []byte) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Get the authorization header and return 401 if there is no header
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			errorString := "Authorization header required"
			log.Printf(errorString)
			http.Error(w, errorString, http.StatusUnauthorized)
			return
		}

		// Get the token from the header and validate it
		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
		token, err := validateJWTToken(tokenString, jwtSecret)
		if err!=nil {
			errorString := fmt.Sprintf("Token validation error: %v", err)
			log.Printf(errorString)
			http.Error(w, errorString, http.StatusUnauthorized)
			return
		}
		if !token.Valid {
			errorString := "Invalid token"
			log.Printf(errorString)
			http.Error(w, errorString, http.StatusUnauthorized)
			return
		}

		log.Println("Token validated successfully; passing request to next handler")
		next.ServeHTTP(w, r)
	})
}

func run() error {
	grpcServerEndpoint := getEnv("CUEBOT_ENDPOINT")
	port := getEnv("REST_PORT")
	jwtSecret := []byte(getEnv("JWT_AUTH_SECRET"))

	ctx := context.Background()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Register gRPC server endpoint
	// Note: Make sure the gRPC server is running properly and accessible
	mux := runtime.NewServeMux()
	opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}

	// Register gRPC handlers
	if err := registerGRPCHandlers(ctx, mux, grpcServerEndpoint, opts); err != nil {
		return fmt.Errorf("failed to register gRPC handlers: %w", err)
	}

	log.Println("All gRPC handlers registered successfully")

	// Create a new HTTP ServeMux with middleware jwtMiddleware to protect the mux
	httpMux := http.NewServeMux()
	httpMux.Handle("/", jwtMiddleware(mux, jwtSecret))

	log.Printf("Starting HTTP server on endpoint: %s, port %s", grpcServerEndpoint, port)

	// Start HTTP server (and proxy calls to gRPC server endpoint)
	return http.ListenAndServe(":" + port, httpMux)
}

func registerGRPCHandlers(ctx context.Context, mux *runtime.ServeMux, grpcServerEndpoint string, opts []grpc.DialOption) error {
	log.Println("Registering gRPC handlers")
	handlers := []func(context.Context, *runtime.ServeMux, string, []grpc.DialOption) error{
		gw.RegisterShowInterfaceHandlerFromEndpoint,
		gw.RegisterFrameInterfaceHandlerFromEndpoint,
		gw.RegisterGroupInterfaceHandlerFromEndpoint,
		gw.RegisterJobInterfaceHandlerFromEndpoint,
		gw.RegisterLayerInterfaceHandlerFromEndpoint,
		gw.RegisterDeedInterfaceHandlerFromEndpoint,
		gw.RegisterHostInterfaceHandlerFromEndpoint,
		gw.RegisterOwnerInterfaceHandlerFromEndpoint,
		gw.RegisterProcInterfaceHandlerFromEndpoint,
	}

	for _, handler := range handlers {
		if err := handler(ctx, mux, grpcServerEndpoint, opts); err != nil {
			log.Printf("Error registering gRPC handler: %v", err)
			return err
		}
	}
	log.Println("All gRPC handlers registered")
	return nil
}

func main() {
	// Set up file to capture all log outputs
	f, err := os.OpenFile("/logs/opencue_gateway.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0666)
	if err != nil {
		log.Fatal(err)
	}
	// Enable output to both Stdout and the log file
	mw := io.MultiWriter(os.Stdout, f)
	defer f.Close()
	log.SetOutput(mw)

	flag.Parse()
	log.Println("Starting main application")

	if err := run(); err != nil {
		grpclog.Fatal(err)
	}
}

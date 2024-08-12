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
	return jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Ensure that the token's signing method is HMAC
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			errorString := fmt.Sprintf("Unexpected signing method: %v", token.Header["alg"])
			log.Printf(errorString)
			return nil, fmt.Errorf(errorString)
		}
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

		// If token is valid, pass it to the next handler
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

	// Create a new HTTP ServeMux with middleware jwtMiddleware to protect the mux
	httpMux := http.NewServeMux()
	httpMux.Handle("/", jwtMiddleware(mux, jwtSecret))
	
	// Start HTTP server (and proxy calls to gRPC server endpoint)
	return http.ListenAndServe(":" + port, httpMux)
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

	if err := run(); err != nil {
		grpclog.Fatal(err)
	}
}
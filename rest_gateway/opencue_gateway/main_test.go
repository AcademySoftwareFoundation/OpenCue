package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
	
	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
)

func TestJwtMiddleware(t *testing.T) {
	os.Setenv("CUEBOT_ENDPOINT", "test_endpoint")
	os.Setenv("REST_PORT", "test_port")
	jwtSecret := []byte("test_secret")

	// Set up a sample handler to use with the middleware
	sampleHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Create a test server with the middleware
	ts := httptest.NewServer(jwtMiddleware(sampleHandler, jwtSecret))
	defer ts.Close()

	t.Run("Valid Token", func(t *testing.T) {
		// Generate a valid token
		token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
			"sub": "test_user",
			"exp": time.Now().Add(time.Hour).Unix(),
		})
		tokenString, err := token.SignedString(jwtSecret)
		assert.NoError(t, err)

		// Create a request with the valid token
		req, err := http.NewRequest("GET", ts.URL, nil)
		assert.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+tokenString)

		// Perform the request
		res, err := http.DefaultClient.Do(req)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, res.StatusCode)
	})

	t.Run("Missing Token", func(t *testing.T) {
		// Create a request without a token
		req, err := http.NewRequest("GET", ts.URL, nil)
		assert.NoError(t, err)

		// Perform the request
		res, err := http.DefaultClient.Do(req)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, res.StatusCode)
	})

	t.Run("Invalid Token", func(t *testing.T) {
		// Create a request with an invalid token
		req, err := http.NewRequest("GET", ts.URL, nil)
		assert.NoError(t, err)
		req.Header.Set("Authorization", "Bearer invalid_token")

		// Perform the request
		res, err := http.DefaultClient.Do(req)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, res.StatusCode)
	})

	t.Run("Expired Token", func(t *testing.T) {
		// Generate an expired token
		token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
			"sub": "test_user",
			"exp": time.Now().Add(-time.Hour).Unix(),
		})
		tokenString, err := token.SignedString(jwtSecret)
		assert.NoError(t, err)

		// Create a request with the expired token
		req, err := http.NewRequest("GET", ts.URL, nil)
		assert.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+tokenString)

		// Perform the request
		res, err := http.DefaultClient.Do(req)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, res.StatusCode)
	})
}

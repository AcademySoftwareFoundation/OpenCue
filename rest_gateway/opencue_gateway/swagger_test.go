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

// Package main provides unit tests for the OpenCue REST Gateway Swagger UI.
//
// This test suite validates:
//   - SWAGGER_ENABLED / SWAGGER_DIR configuration handling
//   - Discovery of generated OpenAPI documents and their display names
//   - Rendering of the Swagger UI page
//   - Routing for /swagger/, /swagger/specs/ and /swagger/assets/
//   - That /swagger/ is reachable without a JWT while the API is not
//
// Running Tests:
//   - Docker (recommended): ./run_tests.sh (select option 1)
//   - Local Go: go test -v .
//   - With coverage: go test -cover -v .
package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newSwaggerDir creates a temporary directory populated with fake generated
// OpenAPI documents, mirroring what protoc-gen-openapiv2 writes at build time.
func newSwaggerDir(t *testing.T) string {
	t.Helper()

	dir := t.TempDir()
	files := map[string]string{
		"job.swagger.json":              `{"swagger":"2.0","info":{"title":"job.proto"}}`,
		"show.swagger.json":             `{"swagger":"2.0","info":{"title":"show.proto"}}`,
		"render_partition.swagger.json": `{"swagger":"2.0","info":{"title":"renderPartition.proto"}}`,
		"notes.txt":                     "not a spec",
	}
	for name, body := range files {
		require.NoError(t, os.WriteFile(filepath.Join(dir, name), []byte(body), 0o644))
	}
	require.NoError(t, os.Mkdir(filepath.Join(dir, "nested"), 0o755))

	return dir
}

// TestSwaggerEnabled verifies how SWAGGER_ENABLED is interpreted.
//
// The Swagger UI is served without authentication, so operators must be able to
// switch it off. It defaults to enabled when the variable is unset.
func TestSwaggerEnabled(t *testing.T) {
	t.Run("Unset Defaults To Enabled", func(t *testing.T) {
		os.Unsetenv("SWAGGER_ENABLED")
		assert.True(t, swaggerEnabled())
	})

	disabling := []string{"false", "FALSE", "False", "0", "no", "off", "  false  "}
	for _, value := range disabling {
		t.Run("Disabled By "+value, func(t *testing.T) {
			t.Setenv("SWAGGER_ENABLED", value)
			assert.False(t, swaggerEnabled())
		})
	}

	enabling := []string{"true", "1", "yes", "anything-else"}
	for _, value := range enabling {
		t.Run("Enabled By "+value, func(t *testing.T) {
			t.Setenv("SWAGGER_ENABLED", value)
			assert.True(t, swaggerEnabled())
		})
	}
}

// TestSwaggerDirectory verifies SWAGGER_DIR handling and its default value.
func TestSwaggerDirectory(t *testing.T) {
	t.Run("Default", func(t *testing.T) {
		os.Unsetenv("SWAGGER_DIR")
		assert.Equal(t, "./gen/openapiv2", swaggerDirectory())
	})

	t.Run("Override", func(t *testing.T) {
		t.Setenv("SWAGGER_DIR", "/app/gen/openapiv2")
		assert.Equal(t, "/app/gen/openapiv2", swaggerDirectory())
	})
}

// TestTitleCase verifies the display-name formatting helper.
//
// This replaces strings.Title, which is deprecated as of Go 1.18.
func TestTitleCase(t *testing.T) {
	cases := map[string]string{
		"job":              "Job",
		"render partition": "Render Partition",
		"renderPartition":  "RenderPartition",
		"":                 "",
	}
	for input, expected := range cases {
		assert.Equal(t, expected, titleCase(input), "titleCase(%q)", input)
	}
}

// TestSwaggerSpecs verifies discovery of generated OpenAPI documents.
//
// Only JSON files directly inside the directory are listed; subdirectories and
// non-JSON files are skipped.
func TestSwaggerSpecs(t *testing.T) {
	dir := newSwaggerDir(t)

	specs, err := swaggerSpecs(dir)
	require.NoError(t, err)

	byName := map[string]string{}
	for _, spec := range specs {
		byName[spec.Name] = spec.URL
	}

	assert.Len(t, specs, 3, "only the three .json files should be listed")
	assert.Equal(t, "/swagger/specs/job.swagger.json", byName["Job Service"])
	assert.Equal(t, "/swagger/specs/show.swagger.json", byName["Show Service"])
	assert.Equal(t, "/swagger/specs/render_partition.swagger.json", byName["Render Partition Service"])

	t.Run("Missing Directory", func(t *testing.T) {
		_, err := swaggerSpecs(filepath.Join(dir, "does-not-exist"))
		assert.Error(t, err)
	})
}

// TestServeSwaggerUI verifies rendering of the Swagger UI page.
func TestServeSwaggerUI(t *testing.T) {
	dir := newSwaggerDir(t)

	t.Run("Renders Spec List", func(t *testing.T) {
		rec := httptest.NewRecorder()
		serveSwaggerUI(rec, dir)

		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, "text/html; charset=utf-8", rec.Header().Get("Content-Type"))

		body := rec.Body.String()
		assert.Contains(t, body, "/swagger/specs/job.swagger.json")
		assert.Contains(t, body, "Job Service")
		// The spec list must be embedded as JS, not HTML-escaped into entities.
		assert.NotContains(t, body, "&#34;")
		// The asset URLs must point at the locally served copies.
		assert.Contains(t, body, "/swagger/assets/swagger-ui-bundle.js")
		assert.NotContains(t, body, "petstore.swagger.io")
	})

	t.Run("Missing Directory Returns 500", func(t *testing.T) {
		rec := httptest.NewRecorder()
		serveSwaggerUI(rec, filepath.Join(dir, "does-not-exist"))

		assert.Equal(t, http.StatusInternalServerError, rec.Code)
	})
}

// TestServeSwaggerSpec verifies serving of individual OpenAPI documents.
//
// Directory listings and path traversal must both be refused. The handler is
// exercised directly here because http.ServeMux cleans traversal sequences out
// of the request path before a handler ever sees them.
func TestServeSwaggerSpec(t *testing.T) {
	dir := newSwaggerDir(t)

	serve := func(path string) *httptest.ResponseRecorder {
		rec := httptest.NewRecorder()
		serveSwaggerSpec(rec, httptest.NewRequest(http.MethodGet, path, nil), dir)
		return rec
	}

	t.Run("Serves Spec", func(t *testing.T) {
		rec := serve("/swagger/specs/job.swagger.json")
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Contains(t, rec.Body.String(), `"swagger":"2.0"`)
	})

	refused := map[string]string{
		"No Directory Listing": "/swagger/specs/",
		"Non JSON File":        "/swagger/specs/notes.txt",
		"Subdirectory":         "/swagger/specs/nested/job.swagger.json",
		"Traversal":            "/swagger/specs/../../etc/passwd",
		"Encoded Traversal":    "/swagger/specs/..%2f..%2fetc%2fpasswd",
		"Unknown Spec":         "/swagger/specs/nope.json",
	}
	for name, path := range refused {
		t.Run(name, func(t *testing.T) {
			assert.Equal(t, http.StatusNotFound, serve(path).Code, "path %q must not be served", path)
		})
	}
}

// TestRegisterSwaggerHandlers verifies the routes mounted for the Swagger UI.
func TestRegisterSwaggerHandlers(t *testing.T) {
	dir := newSwaggerDir(t)
	t.Setenv("SWAGGER_DIR", dir)
	t.Setenv("SWAGGER_ENABLED", "true")

	mux := http.NewServeMux()
	registerSwaggerHandlers(mux)

	ts := httptest.NewServer(mux)
	defer ts.Close()

	get := func(t *testing.T, path string) *http.Response {
		t.Helper()
		res, err := http.Get(ts.URL + path)
		require.NoError(t, err)
		t.Cleanup(func() { res.Body.Close() })
		return res
	}

	served := map[string]string{
		"UI Page":           "/swagger/",
		"Spec Document":     "/swagger/specs/job.swagger.json",
		"Stylesheet":        "/swagger/assets/swagger-ui.css",
		"Bundle Script":     "/swagger/assets/swagger-ui-bundle.js",
		"Standalone Preset": "/swagger/assets/swagger-ui-standalone-preset.js",
	}
	for name, path := range served {
		t.Run(name, func(t *testing.T) {
			assert.Equal(t, http.StatusOK, get(t, path).StatusCode, "path %q should be served", path)
		})
	}

	// The embedded Swagger UI distribution also ships an index.html and a
	// swagger-initializer.js that load https://petstore.swagger.io, plus several
	// megabytes of source maps. None of those belong on an unauthenticated route.
	blocked := map[string]string{
		"Upstream Index":       "/swagger/assets/index.html",
		"Upstream Initializer": "/swagger/assets/swagger-initializer.js",
		"Source Map":           "/swagger/assets/swagger-ui-bundle.js.map",
		"Asset Listing":        "/swagger/assets/",
		"Spec Listing":         "/swagger/specs/",
	}
	for name, path := range blocked {
		t.Run(name, func(t *testing.T) {
			assert.Equal(t, http.StatusNotFound, get(t, path).StatusCode, "path %q must not be served", path)
		})
	}
}

// TestRegisterSwaggerHandlersNotMounted verifies that nothing is mounted when
// the UI is switched off or the generated specs are absent.
func TestRegisterSwaggerHandlersNotMounted(t *testing.T) {
	t.Run("Disabled", func(t *testing.T) {
		t.Setenv("SWAGGER_DIR", newSwaggerDir(t))
		t.Setenv("SWAGGER_ENABLED", "false")

		mux := http.NewServeMux()
		registerSwaggerHandlers(mux)
		mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusTeapot)
		})

		ts := httptest.NewServer(mux)
		defer ts.Close()

		res, err := http.Get(ts.URL + "/swagger/")
		require.NoError(t, err)
		defer res.Body.Close()
		assert.Equal(t, http.StatusTeapot, res.StatusCode, "/swagger/ should fall through to the catch-all handler")
	})

	t.Run("Missing Spec Directory", func(t *testing.T) {
		t.Setenv("SWAGGER_DIR", filepath.Join(t.TempDir(), "does-not-exist"))
		t.Setenv("SWAGGER_ENABLED", "true")

		mux := http.NewServeMux()
		registerSwaggerHandlers(mux)
		mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(http.StatusTeapot)
		})

		ts := httptest.NewServer(mux)
		defer ts.Close()

		res, err := http.Get(ts.URL + "/swagger/")
		require.NoError(t, err)
		defer res.Body.Close()
		assert.Equal(t, http.StatusTeapot, res.StatusCode, "/swagger/ should fall through to the catch-all handler")
	})
}

// TestSwaggerRoutesBypassAuth verifies the authentication boundary.
//
// The Swagger UI is deliberately mounted outside jwtMiddleware so the API can be
// browsed without a token. This test pins that behaviour in both directions: the
// documentation routes must be reachable anonymously, and the API routes must
// still reject anonymous requests.
func TestSwaggerRoutesBypassAuth(t *testing.T) {
	dir := newSwaggerDir(t)
	t.Setenv("SWAGGER_DIR", dir)
	t.Setenv("SWAGGER_ENABLED", "true")

	jwtSecret := []byte("test_secret")
	api := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	mux := http.NewServeMux()
	registerSwaggerHandlers(mux)
	mux.Handle("/", jwtMiddleware(api, jwtSecret))

	ts := httptest.NewServer(mux)
	defer ts.Close()

	anonymous := map[string]string{
		"UI Page":       "/swagger/",
		"Spec Document": "/swagger/specs/job.swagger.json",
		"Stylesheet":    "/swagger/assets/swagger-ui.css",
	}
	for name, path := range anonymous {
		t.Run("Anonymous "+name, func(t *testing.T) {
			res, err := http.Get(ts.URL + path)
			require.NoError(t, err)
			defer res.Body.Close()
			assert.Equal(t, http.StatusOK, res.StatusCode, "%q must be browsable without a token", path)
		})
	}

	t.Run("Anonymous API Request Is Rejected", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/job.JobInterface/GetJob")
		require.NoError(t, err)
		defer res.Body.Close()
		assert.Equal(t, http.StatusUnauthorized, res.StatusCode, "the API must still require a token")
	})

	t.Run("Authenticated API Request Succeeds", func(t *testing.T) {
		token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
			"sub": "test_user",
			"exp": time.Now().Add(time.Hour).Unix(),
		})
		tokenString, err := token.SignedString(jwtSecret)
		require.NoError(t, err)

		req, err := http.NewRequest(http.MethodGet, ts.URL+"/job.JobInterface/GetJob", nil)
		require.NoError(t, err)
		req.Header.Set("Authorization", "Bearer "+tokenString)

		res, err := http.DefaultClient.Do(req)
		require.NoError(t, err)
		defer res.Body.Close()
		assert.Equal(t, http.StatusOK, res.StatusCode)
	})
}

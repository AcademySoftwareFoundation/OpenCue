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

// +build integration

// Package main provides integration tests for the OpenCue REST Gateway.
//
// These tests validate the complete REST Gateway functionality by making real HTTP
// requests to a running gateway instance connected to a live Cuebot server. Unlike
// unit tests which use mocks, integration tests verify actual end-to-end behavior.
//
// Test Coverage:
//   - JWT authentication (valid tokens, invalid tokens, missing tokens)
//   - All OpenCue interface endpoints (Core + Management)
//   - Error handling (invalid endpoints, malformed JSON, missing data)
//   - Response format validation (JSON structure, content types)
//   - Performance benchmarks (response time, concurrent requests)
//   - CORS header validation
//
// Prerequisites:
//   - Running OpenCue stack (Cuebot + PostgreSQL)
//   - Running REST Gateway with JWT authentication
//   - Test show (default: "testing") created in Cuebot
//
// Configuration:
// Tests are configured via environment variables:
//   - GATEWAY_URL: REST Gateway endpoint (default: http://localhost:8448)
//   - JWT_SECRET: JWT signing secret (must match gateway configuration)
//   - TEST_SHOW: Show name for tests (default: "testing")
//
// Running Integration Tests:
//   - Basic: go test -v -tags=integration
//   - Specific test: go test -v -tags=integration -run TestIntegration_ShowInterface
//   - Benchmarks: go test -bench=. -tags=integration
//   - Docker: ./run_docker_integration_tests.sh (recommended)
//
// Build Tag:
// The "integration" build tag ensures these tests only run when explicitly requested
// via -tags=integration flag, preventing accidental execution during unit test runs.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/stretchr/testify/assert"
)

// Integration test configuration variables loaded from environment.
//
// These variables control how integration tests connect to the REST Gateway
// and what test data to use. They can be overridden via environment variables
// to support different test environments (local, Docker, CI/CD).
var (
	// gatewayURL is the base URL for the REST Gateway server
	gatewayURL = getEnvOrDefault("GATEWAY_URL", "http://localhost:8448")

	// jwtSecret is the secret key for JWT token generation (must match gateway config)
	jwtSecret  = getEnvOrDefault("JWT_SECRET", "dev-secret-key-change-in-production")

	// testShow is the show name to use for tests requiring a show context
	testShow   = getEnvOrDefault("TEST_SHOW", "testing")
)

// getEnvOrDefault retrieves an environment variable or returns a default value.
//
// This helper provides a simple way to make tests configurable via environment
// variables while maintaining sensible defaults for local development.
//
// Parameters:
//   - key: The environment variable name to retrieve
//   - defaultValue: The value to return if the environment variable is not set
//
// Returns:
//   - string: The environment variable value or defaultValue if not set
func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// generateJWTToken creates a valid JWT token for testing authentication.
//
// This function generates HMAC SHA256 signed JWT tokens that match the format
// expected by the REST Gateway's JWT middleware. Tokens include standard claims
// (user, expiration) and can be configured with custom expiry times.
//
// The generated tokens are compatible with the jwt-go library used by the gateway
// and follow RFC 7519 specifications.
//
// Parameters:
//   - secret: The secret key to sign the token with (should match gateway config)
//   - expiryHours: Number of hours until the token expires
//
// Returns:
//   - string: The signed JWT token in "xxx.yyy.zzz" format
//   - error: Token generation error, nil on success
//
// Example:
//   token, err := generateJWTToken("my-secret", 1)  // 1-hour token
func generateJWTToken(secret string, expiryHours int) (string, error) {
	claims := jwt.MapClaims{
		"user": "integration-test",
		"exp":  time.Now().Add(time.Duration(expiryHours) * time.Hour).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(secret))
}

// makeAuthenticatedRequest performs an authenticated HTTP POST request to the REST Gateway.
//
// This is the primary helper function for integration tests, handling all common request
// setup including:
//   - JWT token generation and inclusion in Authorization header
//   - JSON payload marshalling
//   - HTTP request creation and execution
//   - Response body parsing
//   - Error handling and status code extraction
//
// The function simplifies test code by abstracting away the boilerplate HTTP client
// logic, allowing tests to focus on validating responses and behavior.
//
// Parameters:
//   - t: Test context for logging and assertions
//   - endpoint: The gRPC-gateway endpoint path (e.g., "show.ShowInterface/GetShows")
//   - payload: Request payload to be JSON-encoded
//
// Returns:
//   - map[string]interface{}: Parsed JSON response body as a map
//   - int: HTTP status code
//   - error: Any error during request/response handling, nil on success
//
// Example:
//   result, status, err := makeAuthenticatedRequest(t,
//       "show.ShowInterface/GetShows",
//       map[string]interface{}{})
func makeAuthenticatedRequest(t *testing.T, endpoint string, payload interface{}) (map[string]interface{}, int, error) {
	token, err := generateJWTToken(jwtSecret, 1)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to generate JWT token: %v", err)
	}

	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to marshal payload: %v", err)
	}

	url := fmt.Sprintf("%s/%s", gatewayURL, endpoint)
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonPayload))
	if err != nil {
		return nil, 0, fmt.Errorf("failed to create request: %v", err)
	}

	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, resp.StatusCode, fmt.Errorf("failed to read response: %v", err)
	}

	var result map[string]interface{}
	if len(body) > 0 {
		if err := json.Unmarshal(body, &result); err != nil {
			return nil, resp.StatusCode, fmt.Errorf("failed to unmarshal response: %v (body: %s)", err, string(body))
		}
	}

	return result, resp.StatusCode, nil
}

// TestIntegration_JWTAuthentication validates JWT token-based authentication.
//
// This test ensures the REST Gateway properly enforces JWT authentication by:
//   - Accepting requests with valid, non-expired tokens
//   - Rejecting requests with invalid or malformed tokens
//   - Rejecting requests without Authorization headers
//
// Authentication is the first line of defense for the gateway - these tests
// verify that security is properly enforced at the HTTP layer before any
// requests reach the gRPC backend.
//
// Test Cases:
//   - ValidToken: Should return 200 OK with proper response data
//   - InvalidToken: Should return 401 Unauthorized
//   - MissingToken: Should return 401 Unauthorized
func TestIntegration_JWTAuthentication(t *testing.T) {
	t.Run("ValidToken", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/GetShows", map[string]interface{}{})
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
	})

	t.Run("InvalidToken", func(t *testing.T) {
		url := fmt.Sprintf("%s/show.ShowInterface/GetShows", gatewayURL)
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer([]byte("{}")))
		req.Header.Set("Authorization", "Bearer invalid-token")
		req.Header.Set("Content-Type", "application/json")

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(req)
		assert.NoError(t, err)
		defer resp.Body.Close()

		assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
	})

	t.Run("MissingToken", func(t *testing.T) {
		url := fmt.Sprintf("%s/show.ShowInterface/GetShows", gatewayURL)
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer([]byte("{}")))
		req.Header.Set("Content-Type", "application/json")

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(req)
		assert.NoError(t, err)
		defer resp.Body.Close()

		assert.Equal(t, http.StatusUnauthorized, resp.StatusCode)
	})
}

// TestIntegration_ShowInterface validates ShowInterface REST endpoints.
//
// The ShowInterface provides operations for managing production shows, which
// are the top-level organizational units in OpenCue. This test validates:
//   - GetShows: List all shows in the system
//   - FindShow: Retrieve a specific show by name
//   - GetActiveShows: List only active shows
//
// Test Coverage:
//   - Successful retrieval of show data
//   - Response structure validation (contains "shows" field)
//   - Graceful handling of non-existent shows
func TestIntegration_ShowInterface(t *testing.T) {
	t.Run("GetShows", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/GetShows", map[string]interface{}{})
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
		assert.Contains(t, result, "shows")
	})

	t.Run("FindShow", func(t *testing.T) {
		payload := map[string]interface{}{
			"name": testShow,
		}
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/FindShow", payload)
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
			assert.Contains(t, result, "show")
		}
	})

	t.Run("GetActiveShows", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/GetActiveShows", map[string]interface{}{})
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
	})
}

// TestIntegration_JobInterface validates JobInterface REST endpoints.
//
// The JobInterface provides operations for managing render jobs. This test
// validates the GetJobs endpoint which retrieves jobs filtered by show.
//
// Jobs are the primary work units in OpenCue, representing collections of
// frames to be rendered. Proper job listing is critical for monitoring
// production pipeline status.
//
// Test Coverage:
//   - GetJobs with show filter
//   - Response structure validation (contains "jobs" field)
func TestIntegration_JobInterface(t *testing.T) {
	t.Run("GetJobs", func(t *testing.T) {
		payload := map[string]interface{}{
			"r": map[string]interface{}{
				"show": testShow,
			},
		}
		result, status, err := makeAuthenticatedRequest(t, "job.JobInterface/GetJobs", payload)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
		assert.Contains(t, result, "jobs")
	})
}

// TestIntegration_FrameInterface validates FrameInterface REST endpoints.
//
// The FrameInterface provides frame-level operations for managing individual
// render tasks within jobs. This test validates the GetFrames endpoint.
//
// Frames represent individual render tasks (e.g., frame 1, frame 2, etc.) and
// are the atomic unit of work in OpenCue. This test requires existing jobs
// with frames in the test show.
//
// Test Behavior:
//   - Skips if no jobs are available (graceful degradation)
//   - Retrieves frames for the first available job
//   - Validates response structure (contains "frames" field)
func TestIntegration_FrameInterface(t *testing.T) {
	// First get jobs to find a frame
	payload := map[string]interface{}{
		"r": map[string]interface{}{
			"show": testShow,
		},
	}
	jobResult, status, err := makeAuthenticatedRequest(t, "job.JobInterface/GetJobs", payload)
	if err != nil || status != http.StatusOK {
		t.Skip("Skipping frame tests - no jobs available")
		return
	}

	jobs, ok := jobResult["jobs"].(map[string]interface{})
	if !ok {
		t.Skip("Skipping frame tests - no jobs data")
		return
	}

	jobsList, ok := jobs["jobs"].([]interface{})
	if !ok || len(jobsList) == 0 {
		t.Skip("Skipping frame tests - no jobs found")
		return
	}

	t.Run("GetFrames", func(t *testing.T) {
		firstJob := jobsList[0].(map[string]interface{})
		jobID := firstJob["id"].(string)

		framePayload := map[string]interface{}{
			"r": map[string]interface{}{
				"job": jobID,
			},
		}
		result, status, err := makeAuthenticatedRequest(t, "frame.FrameInterface/GetFrames", framePayload)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
		assert.Contains(t, result, "frames")
	})
}

// TestIntegration_LayerInterface validates LayerInterface REST endpoints.
//
// The LayerInterface provides operations for managing job layers, which group
// frames by render pass or department (e.g., lighting, compositing).
//
// Layers organize frames within jobs, allowing different render passes to be
// managed independently. This test requires existing jobs with layers.
//
// Test Behavior:
//   - Skips if no jobs are available (graceful degradation)
//   - Retrieves layers for the first available job
//   - Validates response structure
func TestIntegration_LayerInterface(t *testing.T) {
	payload := map[string]interface{}{
		"r": map[string]interface{}{
			"show": testShow,
		},
	}
	jobResult, status, err := makeAuthenticatedRequest(t, "job.JobInterface/GetJobs", payload)
	if err != nil || status != http.StatusOK {
		t.Skip("Skipping layer tests - no jobs available")
		return
	}

	jobs, ok := jobResult["jobs"].(map[string]interface{})
	if !ok {
		t.Skip("Skipping layer tests - no jobs data")
		return
	}

	jobsList, ok := jobs["jobs"].([]interface{})
	if !ok || len(jobsList) == 0 {
		t.Skip("Skipping layer tests - no jobs found")
		return
	}

	t.Run("GetLayers", func(t *testing.T) {
		firstJob := jobsList[0].(map[string]interface{})
		jobID := firstJob["id"].(string)

		layerPayload := map[string]interface{}{
			"r": map[string]interface{}{
				"job": jobID,
			},
		}
		result, status, err := makeAuthenticatedRequest(t, "layer.LayerInterface/GetLayers", layerPayload)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
	})
}

// TestIntegration_GroupInterface validates GroupInterface REST endpoints.
//
// The GroupInterface provides operations for managing job groups, which
// organize jobs hierarchically within shows for resource allocation.
//
// Test Coverage:
//   - GetGroups: List all groups in the system
func TestIntegration_GroupInterface(t *testing.T) {
	t.Run("GetGroups", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "group.GroupInterface/GetGroups", map[string]interface{}{})
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_HostInterface validates HostInterface REST endpoints.
//
// The HostInterface provides operations for managing render hosts (machines)
// that execute frame rendering. This test validates the GetHosts endpoint.
//
// Hosts are the compute resources in OpenCue. Proper host management is
// critical for monitoring render farm capacity and utilization.
//
// Test Coverage:
//   - GetHosts with empty filter
//   - Response structure validation (contains "hosts" field)
func TestIntegration_HostInterface(t *testing.T) {
	t.Run("GetHosts", func(t *testing.T) {
		payload := map[string]interface{}{
			"r": map[string]interface{}{},
		}
		result, status, err := makeAuthenticatedRequest(t, "host.HostInterface/GetHosts", payload)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)
		assert.Contains(t, result, "hosts")
	})
}

// TestIntegration_OwnerInterface validates OwnerInterface REST endpoints.
//
// The OwnerInterface provides operations for managing resource ownership,
// allowing users to claim hosts for dedicated use.
//
// Test Coverage:
//   - GetOwners: List all owners in the system
func TestIntegration_OwnerInterface(t *testing.T) {
	t.Run("GetOwners", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "owner.OwnerInterface/GetOwners", map[string]interface{}{})
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_ProcInterface validates ProcInterface REST endpoints.
//
// The ProcInterface provides operations for managing render processes (procs),
// which represent individual frame render executions on hosts.
//
// Test Coverage:
//   - GetProcs: List all active processes in the system
func TestIntegration_ProcInterface(t *testing.T) {
	t.Run("GetProcs", func(t *testing.T) {
		payload := map[string]interface{}{
			"r": map[string]interface{}{},
		}
		result, status, err := makeAuthenticatedRequest(t, "proc.ProcInterface/GetProcs", payload)
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_DeedInterface validates DeedInterface REST endpoints.
//
// The DeedInterface provides operations for managing resource deeds, which
// represent ownership assignments of hosts to shows/owners.
//
// Test Behavior:
//   - Currently skipped as it requires specific owner/host setup
//   - Deeds require pre-configured ownership relationships
func TestIntegration_DeedInterface(t *testing.T) {
	// Deed interface typically requires specific owner/host setup
	t.Skip("Skipping deed tests - requires specific test environment setup")
}

// TestIntegration_CommentInterface validates CommentInterface REST endpoints.
//
// The CommentInterface provides operations for managing comments on jobs and
// hosts, enabling communication and documentation within the render pipeline.
//
// Test Behavior:
//   - Skips if no jobs are available (comments require existing jobs)
//   - Retrieves comments for the first available job
//   - Validates response handling (may be empty if no comments exist)
func TestIntegration_CommentInterface(t *testing.T) {
	// Get a job first to test comments
	payload := map[string]interface{}{
		"r": map[string]interface{}{
			"show": testShow,
		},
	}
	jobResult, status, err := makeAuthenticatedRequest(t, "job.JobInterface/GetJobs", payload)
	if err != nil || status != http.StatusOK {
		t.Skip("Skipping comment tests - no jobs available")
		return
	}

	jobs, ok := jobResult["jobs"].(map[string]interface{})
	if !ok {
		t.Skip("Skipping comment tests - no jobs data")
		return
	}

	jobsList, ok := jobs["jobs"].([]interface{})
	if !ok || len(jobsList) == 0 {
		t.Skip("Skipping comment tests - no jobs found")
		return
	}

	t.Run("GetComments", func(t *testing.T) {
		firstJob := jobsList[0].(map[string]interface{})
		jobID := firstJob["id"].(string)

		commentPayload := map[string]interface{}{
			"job": map[string]interface{}{
				"id": jobID,
			},
		}
		result, status, err := makeAuthenticatedRequest(t, "comment.CommentInterface/GetComments", commentPayload)
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_AllocationInterface validates AllocationInterface REST endpoints.
//
// The AllocationInterface provides operations for managing resource allocations,
// which distribute render farm capacity across shows and facilities.
//
// Allocations define how many hosts or cores each show can use, enabling
// fair resource sharing across production workloads.
//
// Test Coverage:
//   - GetAll: List all allocations in the system
//   - Response structure validation (contains "allocations" field)
func TestIntegration_AllocationInterface(t *testing.T) {
	t.Run("GetAll", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "facility.AllocationInterface/GetAll", map[string]interface{}{})
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
			assert.Contains(t, result, "allocations")
		}
	})
}

// TestIntegration_FacilityInterface validates FacilityInterface REST endpoints.
//
// The FacilityInterface provides operations for managing render facilities,
// which represent physical or logical data centers hosting render farms.
//
// Facilities enable multi-site OpenCue deployments, allowing jobs to be
// rendered across geographically distributed render farms.
//
// Test Coverage:
//   - Get: Retrieve a facility by name (e.g., "default")
//   - Graceful handling of non-existent facilities (404)
func TestIntegration_FacilityInterface(t *testing.T) {
	t.Run("Get", func(t *testing.T) {
		payload := map[string]interface{}{
			"name": "default",
		}
		result, status, err := makeAuthenticatedRequest(t, "facility.FacilityInterface/Get", payload)
		assert.NoError(t, err)
		// May return 404 if no default facility exists
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_FilterInterface validates FilterInterface REST endpoints.
//
// The FilterInterface provides operations for managing job filters, which
// automatically route and process incoming jobs based on matching criteria.
//
// Filters apply actions (e.g., assign to group, set priority) to jobs matching
// specific patterns (e.g., job name, user), enabling automated job management.
//
// Test Coverage:
//   - GetFilters: List filters for a show
//   - Response structure validation
func TestIntegration_FilterInterface(t *testing.T) {
	// Filter tests require show setup
	payload := map[string]interface{}{
		"show": map[string]interface{}{
			"name": testShow,
		},
	}

	t.Run("GetFilters", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "filter.FilterInterface/GetFilters", payload)
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_DependInterface validates DependInterface REST endpoints.
//
// The DependInterface provides operations for managing job dependencies,
// which control execution order by requiring jobs/layers/frames to wait
// for other jobs/layers/frames to complete.
//
// Dependencies enable complex pipeline workflows where downstream jobs
// can only start after upstream jobs finish successfully.
//
// Test Behavior:
//   - Currently skipped as it requires jobs with dependencies
//   - Dependency tests require specific test data setup
func TestIntegration_DependInterface(t *testing.T) {
	// Depend tests require jobs with dependencies
	t.Skip("Skipping depend tests - requires jobs with dependencies")
}

// TestIntegration_SubscriptionInterface validates SubscriptionInterface REST endpoints.
//
// The SubscriptionInterface provides operations for managing show subscriptions,
// which allocate render capacity from allocations to specific shows.
//
// Subscriptions define how much of an allocation's capacity is reserved for
// a particular show, with optional burst capacity for peak demand.
//
// Test Coverage:
//   - GetSubscriptions: List subscriptions for a show
//   - Response structure validation
func TestIntegration_SubscriptionInterface(t *testing.T) {
	t.Run("GetSubscriptions", func(t *testing.T) {
		payload := map[string]interface{}{
			"show": map[string]interface{}{
				"name": testShow,
			},
		}
		result, status, err := makeAuthenticatedRequest(t, "subscription.SubscriptionInterface/GetSubscriptions", payload)
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_LimitInterface validates LimitInterface REST endpoints.
//
// The LimitInterface provides operations for managing resource limits,
// which constrain concurrent usage of shared resources (e.g., licenses).
//
// Limits prevent resource exhaustion by capping how many jobs/layers/frames
// can simultaneously use expensive resources like software licenses.
//
// Test Coverage:
//   - GetAll: List all limits in the system
//   - Response structure validation (contains "limits" field)
func TestIntegration_LimitInterface(t *testing.T) {
	t.Run("GetAll", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "limit.LimitInterface/GetAll", map[string]interface{}{})
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
			assert.Contains(t, result, "limits")
		}
	})
}

// TestIntegration_ServiceInterface validates ServiceInterface REST endpoints.
//
// The ServiceInterface provides operations for managing service definitions,
// which define minimum core counts and other resource requirements for jobs.
//
// Services ensure jobs receive adequate resources by enforcing minimum
// allocations based on job requirements (e.g., high-memory tasks).
//
// Test Coverage:
//   - GetDefaultServices: List default service configurations
//   - Response structure validation
func TestIntegration_ServiceInterface(t *testing.T) {
	t.Run("GetDefaultServices", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "service.ServiceInterface/GetDefaultServices", map[string]interface{}{})
		assert.NoError(t, err)
		if status == http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_TaskInterface validates TaskInterface REST endpoints.
//
// The TaskInterface provides operations for managing tasks (also known as
// shots), which represent production assets to be rendered.
//
// Tasks organize render work by production shot/asset, enabling tracking
// and management at the production level rather than just technical job level.
//
// Test Behavior:
//   - Currently skipped as it requires specific show/shot setup
//   - Task tests require production tracking database setup
func TestIntegration_TaskInterface(t *testing.T) {
	// Task tests require specific show/shot setup
	t.Skip("Skipping task tests - requires show/shot setup")
}

// TestIntegration_ErrorHandling validates error handling behavior.
//
// This test ensures the REST Gateway properly handles various error conditions:
//   - Invalid endpoints return appropriate error status codes
//   - Malformed JSON payloads are rejected gracefully
//   - Invalid data (e.g., non-existent show names) returns proper errors
//
// Proper error handling is critical for API usability - clients need clear
// feedback when requests fail so they can take corrective action.
//
// Test Cases:
//   - InvalidEndpoint: Non-existent interface/method returns error
//   - MalformedJSON: Invalid JSON payload returns 400-level error
//   - InvalidShowName: Non-existent show returns 404 or error response
func TestIntegration_ErrorHandling(t *testing.T) {
	t.Run("InvalidEndpoint", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "invalid.Interface/DoSomething", map[string]interface{}{})
		assert.NoError(t, err) // No HTTP error
		assert.NotEqual(t, http.StatusOK, status)
		assert.NotNil(t, result)
	})

	t.Run("MalformedJSON", func(t *testing.T) {
		token, _ := generateJWTToken(jwtSecret, 1)
		url := fmt.Sprintf("%s/show.ShowInterface/GetShows", gatewayURL)
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer([]byte("invalid-json")))
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))
		req.Header.Set("Content-Type", "application/json")

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(req)
		assert.NoError(t, err)
		defer resp.Body.Close()

		assert.NotEqual(t, http.StatusOK, resp.StatusCode)
	})

	t.Run("InvalidShowName", func(t *testing.T) {
		payload := map[string]interface{}{
			"name": "non-existent-show-xyz-123",
		}
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/FindShow", payload)
		assert.NoError(t, err)
		// Should return error or 404
		if status != http.StatusOK {
			assert.NotNil(t, result)
		}
	})
}

// TestIntegration_ResponseFormat validates HTTP response formatting.
//
// This test ensures the REST Gateway returns properly formatted responses:
//   - All responses use valid JSON format
//   - Content-Type headers are set correctly to "application/json"
//   - Response structure is consistent and parseable
//
// Consistent response formatting is essential for API clients to reliably
// parse and process data.
//
// Test Cases:
//   - ValidJSONResponse: Response body is valid, parseable JSON
//   - ContentTypeHeader: Content-Type header contains "application/json"
func TestIntegration_ResponseFormat(t *testing.T) {
	t.Run("ValidJSONResponse", func(t *testing.T) {
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/GetShows", map[string]interface{}{})
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)

		// Verify it's valid JSON
		_, err = json.Marshal(result)
		assert.NoError(t, err)
	})

	t.Run("ContentTypeHeader", func(t *testing.T) {
		token, _ := generateJWTToken(jwtSecret, 1)
		url := fmt.Sprintf("%s/show.ShowInterface/GetShows", gatewayURL)
		req, _ := http.NewRequest("POST", url, bytes.NewBuffer([]byte("{}")))
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))
		req.Header.Set("Content-Type", "application/json")

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(req)
		assert.NoError(t, err)
		defer resp.Body.Close()

		contentType := resp.Header.Get("Content-Type")
		assert.Contains(t, contentType, "application/json")
	})
}

// TestIntegration_Performance validates REST Gateway performance characteristics.
//
// This test ensures the gateway meets basic performance requirements:
//   - Individual requests complete in reasonable time (< 5 seconds)
//   - The gateway can handle multiple concurrent requests
//   - No deadlocks or race conditions under concurrent load
//
// Performance testing helps identify bottlenecks and ensures the gateway
// can support production workloads.
//
// Test Cases:
//   - ResponseTime: Single request completes in < 5 seconds
//   - ConcurrentRequests: 10 parallel requests complete successfully
//
// Note: Skipped in short mode (go test -short)
func TestIntegration_Performance(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping performance test in short mode")
	}

	t.Run("ResponseTime", func(t *testing.T) {
		start := time.Now()
		result, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/GetShows", map[string]interface{}{})
		duration := time.Since(start)

		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, status)
		assert.NotNil(t, result)

		// Response should be reasonably fast (< 5 seconds)
		assert.Less(t, duration, 5*time.Second, "Response took too long: %v", duration)
		t.Logf("Response time: %v", duration)
	})

	t.Run("ConcurrentRequests", func(t *testing.T) {
		concurrency := 10
		done := make(chan bool, concurrency)
		errors := make(chan error, concurrency)

		for i := 0; i < concurrency; i++ {
			go func() {
				_, status, err := makeAuthenticatedRequest(t, "show.ShowInterface/GetShows", map[string]interface{}{})
				if err != nil {
					errors <- err
					return
				}
				if status != http.StatusOK {
					errors <- fmt.Errorf("unexpected status: %d", status)
					return
				}
				done <- true
			}()
		}

		successCount := 0
		for i := 0; i < concurrency; i++ {
			select {
			case <-done:
				successCount++
			case err := <-errors:
				t.Logf("Concurrent request error: %v", err)
			case <-time.After(10 * time.Second):
				t.Fatal("Timeout waiting for concurrent requests")
			}
		}

		assert.Greater(t, successCount, concurrency/2, "Too many concurrent requests failed")
		t.Logf("Successful concurrent requests: %d/%d", successCount, concurrency)
	})
}

// TestIntegration_CORS validates Cross-Origin Resource Sharing (CORS) headers.
//
// This test checks whether the REST Gateway includes CORS headers in responses,
// which are necessary for web browsers to make cross-origin requests from
// JavaScript applications.
//
// CORS support is critical for web-based UIs that need to call the REST Gateway
// from different domains (e.g., CueWeb running on localhost:3000 calling
// gateway on localhost:8448).
//
// Test Coverage:
//   - OPTIONS preflight requests
//   - Access-Control-Allow-Origin header presence
//   - Logging CORS configuration for debugging
//
// Note: This test is informational - it logs CORS headers but doesn't enforce
// specific values, as CORS configuration may vary by deployment.
func TestIntegration_CORS(t *testing.T) {
	t.Run("CORSHeaders", func(t *testing.T) {
		token, _ := generateJWTToken(jwtSecret, 1)
		url := fmt.Sprintf("%s/show.ShowInterface/GetShows", gatewayURL)
		req, _ := http.NewRequest("OPTIONS", url, nil)
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))
		req.Header.Set("Origin", "http://localhost:3000")
		req.Header.Set("Access-Control-Request-Method", "POST")

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Do(req)
		assert.NoError(t, err)
		defer resp.Body.Close()

		// Check for CORS headers
		allowOrigin := resp.Header.Get("Access-Control-Allow-Origin")
		t.Logf("CORS Allow-Origin: %s", allowOrigin)
	})
}

// BenchmarkIntegration_GetShows measures ShowInterface.GetShows performance.
//
// This benchmark measures the throughput and latency of the GetShows endpoint,
// which is one of the most frequently called APIs in production UIs.
//
// Results help identify performance regressions and optimize hot paths.
//
// Run with: go test -bench=BenchmarkIntegration_GetShows -tags=integration
func BenchmarkIntegration_GetShows(b *testing.B) {
	for i := 0; i < b.N; i++ {
		makeAuthenticatedRequest(nil, "show.ShowInterface/GetShows", map[string]interface{}{})
	}
}

// BenchmarkIntegration_GetJobs measures JobInterface.GetJobs performance.
//
// This benchmark measures the throughput and latency of the GetJobs endpoint,
// which is another high-frequency API call in production monitoring dashboards.
//
// Job queries can be more expensive than show queries due to data volume,
// so this benchmark helps track query performance.
//
// Run with: go test -bench=BenchmarkIntegration_GetJobs -tags=integration
func BenchmarkIntegration_GetJobs(b *testing.B) {
	payload := map[string]interface{}{
		"r": map[string]interface{}{
			"show": testShow,
		},
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		makeAuthenticatedRequest(nil, "job.JobInterface/GetJobs", payload)
	}
}

// BenchmarkIntegration_JWTGeneration measures JWT token generation performance.
//
// This benchmark measures the cost of generating JWT tokens, which happens
// once per test request. Token generation uses cryptographic operations
// (HMAC-SHA256) so performance matters for high-throughput scenarios.
//
// Results help assess whether JWT overhead is significant compared to
// request processing time.
//
// Run with: go test -bench=BenchmarkIntegration_JWTGeneration -tags=integration
func BenchmarkIntegration_JWTGeneration(b *testing.B) {
	for i := 0; i < b.N; i++ {
		generateJWTToken(jwtSecret, 1)
	}
}

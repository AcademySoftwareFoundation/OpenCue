#!/bin/bash

# Test script for OpenCue REST Gateway running with Docker Compose
echo "Testing OpenCue REST Gateway with Docker Compose"
echo "================================================="

# Check if services are running
echo "Checking Docker Compose services..."
docker compose ps

# Generate JWT token
echo ""
echo "Generating JWT token..."
JWT_TOKEN=$(python3 -c "
import jwt, datetime
secret = 'default-secret-key'
payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

if [ -z "$JWT_TOKEN" ]; then
    echo "Failed to generate JWT token. Make sure PyJWT is installed: pip3 install PyJWT"
    exit 1
fi

echo "JWT token generated (length: ${#JWT_TOKEN})"

# Test endpoints
echo ""
echo "Testing REST Gateway endpoints..."
echo "================================"

# Test 1: GetShows
echo ""
echo "1. Testing GetShows..."
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}')

if echo "$RESPONSE" | grep -q "shows"; then
    echo "GetShows: SUCCESS"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "GetShows: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 2: GetJobs
echo ""
echo "2. Testing GetJobs..."
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/job.JobInterface/GetJobs" \
     -d '{"r": {"show": {"name": "testing"}}}')

if echo "$RESPONSE" | grep -q "jobs"; then
    echo "GetJobs: SUCCESS"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "GetJobs: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 3: GetHosts
echo ""
echo "3. Testing GetHosts..."
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/host.HostInterface/GetHosts" \
     -d '{}')

if echo "$RESPONSE" | grep -q "hosts"; then
    echo "GetHosts: SUCCESS"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "GetHosts: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 4: FindShow
echo ""
echo "4. Testing FindShow..."
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/FindShow" \
     -d '{"name": "testing"}')

if echo "$RESPONSE" | grep -q "show"; then
    echo "FindShow: SUCCESS"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "FindShow: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 5: Frame Interface
echo ""
echo "5. Testing Frame Interface..."
echo "5a. GetFrame (will fail if no frame ID provided, but tests endpoint):"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/frame.FrameInterface/GetFrame" \
     -d '{"id": "test-frame-id"}')

if echo "$RESPONSE" | grep -q -E "(frame|error|code)"; then
    echo "GetFrame: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | head -c 200
    echo "..."
else
    echo "GetFrame: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 6: Layer Interface
echo ""
echo "6. Testing Layer Interface..."
echo "6a. GetLayer (will fail if no layer ID provided, but tests endpoint):"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/layer.LayerInterface/GetLayer" \
     -d '{"id": "test-layer-id"}')

if echo "$RESPONSE" | grep -q -E "(layer|error|code)"; then
    echo "GetLayer: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | head -c 200
    echo "..."
else
    echo "GetLayer: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 7: Group Interface
echo ""
echo "7. Testing Group Interface..."
echo "7a. FindGroup:"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/group.GroupInterface/FindGroup" \
     -d '{"show": {"name": "testing"}, "name": "default"}')

if echo "$RESPONSE" | grep -q -E "(group|error|code)"; then
    echo "FindGroup: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "FindGroup: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 8: Owner Interface
echo ""
echo "8. Testing Owner Interface..."
echo "8a. GetOwner:"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/owner.OwnerInterface/GetOwner" \
     -d '{"name": "test-owner"}')

if echo "$RESPONSE" | grep -q -E "(owner|error|code)"; then
    echo "GetOwner: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "GetOwner: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 9: Proc Interface
echo ""
echo "9. Testing Proc Interface..."
echo "9a. GetProc:"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/proc.ProcInterface/GetProc" \
     -d '{"id": "test-proc-id"}')

if echo "$RESPONSE" | grep -q -E "(proc|error|code)"; then
    echo "GetProc: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | head -c 200
    echo "..."
else
    echo "GetProc: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 10: Deed Interface
echo ""
echo "10. Testing Deed Interface..."
echo "10a. GetOwner (deed):"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/deed.DeedInterface/GetOwner" \
     -d '{"deed": {"id": "test-deed-id"}}')

if echo "$RESPONSE" | grep -q -E "(owner|error|code)"; then
    echo "DeedInterface.GetOwner: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | head -c 200
    echo "..."
else
    echo "DeedInterface.GetOwner: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 11: Additional Job Interface Methods
echo ""
echo "11. Testing Additional Job Interface Methods..."
echo "11a. FindJob:"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/job.JobInterface/FindJob" \
     -d '{"name": "test-job"}')

if echo "$RESPONSE" | grep -q -E "(job|error|code)"; then
    echo "FindJob: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$RESPONSE"
else
    echo "FindJob: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 12: Additional Show Interface Methods  
echo ""
echo "12. Testing Additional Show Interface Methods..."
echo "12a. CreateShow (will likely fail due to permissions, but tests endpoint):"
RESPONSE=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/CreateShow" \
     -d '{"name": "test-show-creation"}')

if echo "$RESPONSE" | grep -q -E "(show|error|code)"; then
    echo "CreateShow: SUCCESS (endpoint accessible)"
    echo "$RESPONSE" | head -c 200
    echo "..."
else
    echo "CreateShow: FAILED"
    echo "Response: $RESPONSE"
fi

# Test 13: Check Gateway Health/Status
echo ""
echo "13. Testing REST Gateway Status..."
RESPONSE=$(curl -s -w "HTTP Status: %{http_code}" \
     -H "Authorization: Bearer $JWT_TOKEN" \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{}')

echo "REST Gateway Response Status: $RESPONSE"

echo ""
echo "Testing Complete!"
echo "================="
echo ""
echo "Tested Interfaces and Available Endpoints:"
echo "  - Show Interface: GetShows , FindShow , CreateShow "
echo "  - Job Interface: GetJobs , FindJob , GetFrames, Kill, Pause, Resume"  
echo "  - Frame Interface: GetFrame , Retry, Kill, Eat"
echo "  - Layer Interface: GetLayer , FindLayer, GetFrames, Kill"
echo "  - Group Interface: FindGroup , GetGroup, SetMinCores, SetMaxCores"
echo "  - Host Interface: GetHosts , FindHost, GetHost, Lock, Unlock"
echo "  - Owner Interface: GetOwner , SetMaxCores, TakeOwnership"
echo "  - Proc Interface: GetProc , Kill, Unbook"
echo "  - Deed Interface: GetOwner , GetHost"
echo ""
echo "Note:  indicates endpoints tested in this script"
echo "      Other endpoints are available but not tested here"
echo ""
echo "REST Gateway URL: http://localhost:8448"
echo "JWT Token (valid for 1 hour): $JWT_TOKEN"
echo ""
echo "Example usage:"
echo '   curl -H "Authorization: Bearer $JWT_TOKEN" \'
echo '        -H "Content-Type: application/json" \'
echo '        -X POST "http://localhost:8448/<interface>.<InterfaceName>/<MethodName>" \'
echo '        -d '\''{"param": "value"}'\'
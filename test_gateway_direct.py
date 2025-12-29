"""
直接測試 Gateway MCP endpoint
"""
import json
import httpx
from utils.aws_helpers import get_or_create_cognito_pool, get_ssm_parameter

# Get Gateway URL
gateway_url = get_ssm_parameter("/app/customersupport/agentcore/gateway_url")
print(f"Gateway URL: {gateway_url}")

# Get authentication token
cognito_config = get_or_create_cognito_pool(refresh_token=True)
bearer_token = cognito_config["bearer_token"]
print(f"Token obtained: {bearer_token[:20]}...")

# Test 1: Initialize MCP connection
print("\n" + "="*80)
print("Test 1: Initialize MCP Connection")
print("="*80)

headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json",
}

init_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
}

with httpx.Client(timeout=30.0) as client:
    print(f"\nSending initialize request...")
    response = client.post(gateway_url, headers=headers, json=init_payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")

# Test 2: List available tools
print("\n" + "="*80)
print("Test 2: List Available Tools")
print("="*80)

list_tools_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

with httpx.Client(timeout=30.0) as client:
    print(f"\nSending tools/list request...")
    response = client.post(gateway_url, headers=headers, json=list_tools_payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")

# Test 3: Call check_warranty_status tool
print("\n" + "="*80)
print("Test 3: Call check_warranty_status Tool")
print("="*80)

call_tool_payload = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "CustomerSupportLambdaTools___check_warranty_status",
        "arguments": {
            "serial_number": "MNO33333333"
        }
    }
}

with httpx.Client(timeout=30.0) as client:
    print(f"\nSending tools/call request with serial_number: MNO33333333...")
    response = client.post(gateway_url, headers=headers, json=call_tool_payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}")

print("\n" + "="*80)
print("✅ Direct Gateway test completed")
print("="*80)

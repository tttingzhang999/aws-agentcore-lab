#!/usr/bin/env python3
"""
Setup script for AgentCore Gateway.

This script:
1. Creates an AgentCore Gateway with Cognito authentication
2. Adds Lambda function as a target with tool definitions
3. Stores configuration in SSM Parameter Store
"""

import os
import sys
import time

import boto3

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.aws_helpers import (
    get_aws_region,
    get_or_create_cognito_pool,
    get_ssm_parameter,
    load_api_spec,
    put_ssm_parameter,
)

# Initialize AWS clients
REGION = get_aws_region()
gateway_client = boto3.client("bedrock-agentcore-control", region_name=REGION)


def create_gateway(gateway_name: str) -> dict:
    """
    Create an AgentCore Gateway with Cognito authentication.

    Args:
        gateway_name: Name for the gateway

    Returns:
        Dictionary with gateway details (id, name, url, arn)
    """
    print(f"\n📡 Creating AgentCore Gateway: {gateway_name}")

    # Get Cognito configuration
    cognito_config = get_or_create_cognito_pool()
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [cognito_config["client_id"]],
            "discoveryUrl": cognito_config["discovery_url"],
        }
    }

    try:
        # Try to get existing gateway
        existing_gateway_id = get_ssm_parameter("/app/customersupport/agentcore/gateway_id")

        if existing_gateway_id:
            print(f"✅ Found existing gateway: {existing_gateway_id}")
            gateway_response = gateway_client.get_gateway(gatewayIdentifier=existing_gateway_id)

            gateway = {
                "id": existing_gateway_id,
                "name": gateway_response["name"],
                "gateway_url": gateway_response["gatewayUrl"],
                "gateway_arn": gateway_response["gatewayArn"],
            }
            return gateway

    except Exception:
        print("No existing gateway found, creating new one...")

    # Create new gateway
    create_response = gateway_client.create_gateway(
        name=gateway_name,
        roleArn=get_ssm_parameter("/app/customersupport/agentcore/gateway_iam_role"),
        protocolType="MCP",
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration=auth_config,
        description="Customer Support AgentCore Gateway for Lab 3",
    )

    gateway_id = create_response["gatewayId"]

    # Store gateway configuration
    put_ssm_parameter("/app/customersupport/agentcore/gateway_id", gateway_id)
    put_ssm_parameter("/app/customersupport/agentcore/gateway_name", gateway_name)
    put_ssm_parameter("/app/customersupport/agentcore/gateway_arn", create_response["gatewayArn"])
    put_ssm_parameter("/app/customersupport/agentcore/gateway_url", create_response["gatewayUrl"])

    gateway = {
        "id": gateway_id,
        "name": gateway_name,
        "gateway_url": create_response["gatewayUrl"],
        "gateway_arn": create_response["gatewayArn"],
    }

    print("✅ Gateway created successfully!")
    print(f"   Gateway ID: {gateway_id}")
    print(f"   Gateway URL: {gateway['gateway_url']}")

    # Wait for gateway to be active
    print("   ⏳ Waiting for gateway to become ACTIVE...")
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        try:
            status_response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            status = status_response.get("status", "UNKNOWN")

            if status == "ACTIVE":
                print("   ✅ Gateway is now ACTIVE")
                break
            elif status == "FAILED":
                raise Exception("Gateway creation failed")
            else:
                print(f"   ⏳ Gateway status: {status}, waiting... ({attempt + 1}/{max_attempts})")
                time.sleep(10)
                attempt += 1
        except Exception as e:
            if "ResourceNotFoundException" in str(e):
                # Gateway not found yet, wait
                time.sleep(10)
                attempt += 1
            else:
                raise

    if attempt >= max_attempts:
        raise Exception("Timeout waiting for gateway to become ACTIVE")

    return gateway


def add_lambda_target(gateway_id: str, api_spec_file: str) -> str:
    """
    Add Lambda function as a gateway target.

    Args:
        gateway_id: The gateway ID
        api_spec_file: Path to the API specification JSON file

    Returns:
        The target ID
    """
    print("\n🔧 Adding Lambda target to gateway...")

    # Validate API spec file
    if not os.path.exists(api_spec_file):
        raise FileNotFoundError(f"API spec file not found: {api_spec_file}")

    # Load API specification
    api_spec = load_api_spec(api_spec_file)
    print(f"   Loaded {len(api_spec)} tool definitions from {api_spec_file}")

    # Configure Lambda target
    lambda_target_config = {
        "mcp": {
            "lambda": {
                "lambdaArn": get_ssm_parameter("/app/customersupport/agentcore/lambda_arn"),
                "toolSchema": {"inlinePayload": api_spec},
            }
        }
    }

    # Create gateway target
    credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

    try:
        create_target_response = gateway_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name="CustomerSupportLambdaTools",
            description="Lambda tools for check_warranty_status and web_search",
            targetConfiguration=lambda_target_config,
            credentialProviderConfigurations=credential_config,
        )

        target_id = create_target_response["targetId"]

        print("✅ Lambda target created successfully!")
        print(f"   Target ID: {target_id}")
        print(f"   Available tools: {', '.join([tool['name'] for tool in api_spec])}")

        return target_id

    except Exception as e:
        print(f"❌ Error creating gateway target: {str(e)}")
        raise


def main():
    """Main setup function."""
    print("=" * 70)
    print("🚀 AgentCore Gateway Setup (Lab 3)")
    print("=" * 70)

    try:
        # Step 1: Create Gateway
        gateway_name = "customersupport-gw"
        gateway = create_gateway(gateway_name)

        # Step 2: Add Lambda Target
        api_spec_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "prerequisite",
            "lambda",
            "api_spec.json"
        )
        target_id = add_lambda_target(gateway["id"], api_spec_file)

        # Summary
        print("\n" + "=" * 70)
        print("✅ Gateway Setup Complete!")
        print("=" * 70)
        print("\n📊 Summary:")
        print(f"   Gateway Name: {gateway['name']}")
        print(f"   Gateway ID: {gateway['id']}")
        print(f"   Gateway URL: {gateway['gateway_url']}")
        print(f"   Target ID: {target_id}")
        print("\n🔐 Authentication: Cognito JWT")
        client_id = get_ssm_parameter('/app/customersupport/agentcore/machine_client_id')
        print(f"   Client ID: {client_id}")
        print("\n📝 Next Steps:")
        print("   1. Your agent is now configured to use Gateway MCP tools")
        print("   2. Test with: python test_agent_local.py")
        print("   3. Deploy to AgentCore Runtime (next step)")

    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
诊断 Cognito JWT 认证问题

检查:
1. Cognito token 是否能正确获取
2. JWT token 的内容和有效性
3. Gateway JWT authorizer 配置
"""

import base64
import json
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.aws_helpers import get_or_create_cognito_pool, get_ssm_parameter


def decode_jwt(token: str) -> dict:
    """解码 JWT token（不验证签名）"""
    try:
        # JWT 格式: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}

        # Decode payload (base64url)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 70)
    print("🔍 Cognito JWT 认证诊断")
    print("=" * 70)

    # Step 1: Get Cognito configuration
    print("\n📋 Step 1: 获取 Cognito 配置")
    print("-" * 70)

    try:
        client_id = get_ssm_parameter("/app/customersupport/agentcore/machine_client_id")
        user_pool_id = get_ssm_parameter("/app/customersupport/agentcore/cognito_user_pool_id")
        discovery_url = get_ssm_parameter("/app/customersupport/agentcore/cognito_discovery_url")

        print(f"✅ Client ID: {client_id}")
        print(f"✅ User Pool ID: {user_pool_id}")
        print(f"✅ Discovery URL: {discovery_url}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Step 2: Get authentication token
    print("\n🔑 Step 2: 获取认证 Token")
    print("-" * 70)

    try:
        config = get_or_create_cognito_pool(refresh_token=True)
        id_token = config["bearer_token"]
        access_token = config["access_token"]

        print(f"✅ ID Token (前30字符): {id_token[:30]}...")
        print(f"✅ Access Token (前30字符): {access_token[:30]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Step 3: Decode and inspect ID token
    print("\n🔍 Step 3: 解码 ID Token")
    print("-" * 70)

    id_payload = decode_jwt(id_token)
    if "error" in id_payload:
        print(f"❌ Error decoding ID token: {id_payload['error']}")
    else:
        print("✅ ID Token Payload:")
        for key, value in id_payload.items():
            print(f"   {key}: {value}")

    # Step 4: Check app client settings
    print("\n⚙️  Step 4: 检查 App Client 配置")
    print("-" * 70)

    cognito_client = boto3.client("cognito-idp")
    try:
        response = cognito_client.describe_user_pool_client(
            UserPoolId=user_pool_id, ClientId=client_id
        )

        client_config = response["UserPoolClient"]
        print(f"✅ Client Name: {client_config.get('ClientName')}")
        print(f"   Explicit Auth Flows: {client_config.get('ExplicitAuthFlows', [])}")
        print(f"   Token Validity:")
        print(f"     - ID Token: {client_config.get('IdTokenValidity', 'N/A')} hours")
        print(f"     - Access Token: {client_config.get('AccessTokenValidity', 'N/A')} hours")
        print(f"     - Refresh Token: {client_config.get('RefreshTokenValidity', 'N/A')} days")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Step 5: Check Gateway configuration
    print("\n🌐 Step 5: 检查 Gateway JWT Authorizer 配置")
    print("-" * 70)

    gateway_client = boto3.client("bedrock-agentcore-control")
    try:
        gateway_id = get_ssm_parameter("/app/customersupport/agentcore/gateway_id")
        response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)

        print(f"✅ Gateway ID: {gateway_id}")
        print(f"   Status: {response.get('status')}")
        print(f"   Authorizer Type: {response.get('authorizerType')}")

        auth_config = response.get("authorizerConfiguration", {})
        jwt_config = auth_config.get("customJWTAuthorizer", {})

        print(f"   JWT Authorizer Config:")
        print(f"     - Discovery URL: {jwt_config.get('discoveryUrl')}")
        print(f"     - Allowed Clients: {jwt_config.get('allowedClients', [])}")

        # Check if client_id matches
        allowed_clients = jwt_config.get("allowedClients", [])
        if client_id in allowed_clients:
            print(f"   ✅ Client ID 在允许列表中")
        else:
            print(f"   ❌ Client ID 不在允许列表中！")
            print(f"      当前 Client ID: {client_id}")
            print(f"      允许的 Clients: {allowed_clients}")

        # Check if discovery URLs match
        if jwt_config.get("discoveryUrl") == discovery_url:
            print(f"   ✅ Discovery URL 匹配")
        else:
            print(f"   ❌ Discovery URL 不匹配！")
            print(f"      Gateway: {jwt_config.get('discoveryUrl')}")
            print(f"      Cognito: {discovery_url}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("📊 诊断建议")
    print("=" * 70)

    print("\n如果看到 401 错误，检查以下几点：")
    print("1. Client ID 是否在 Gateway 的 allowedClients 列表中")
    print("2. Discovery URL 是否匹配")
    print("3. Token 是否过期（检查 token validity 设置）")
    print("4. App Client 是否启用了 USER_PASSWORD_AUTH flow")
    print("\n常见解决方法：")
    print("- 重新运行: python scripts/setup_prerequisites.py")
    print("- 重新运行: python scripts/setup_gateway.py")
    print("- 检查 Cognito User Pool 的 App Client 设置")


if __name__ == "__main__":
    main()

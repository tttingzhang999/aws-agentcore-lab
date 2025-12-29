#!/usr/bin/env python3
"""
Setup prerequisites for AgentCore Gateway.

This script creates:
1. Cognito User Pool for authentication
2. IAM Role for Gateway
3. Lambda function and IAM role
4. DynamoDB table for warranty data
5. Stores all configuration in SSM Parameter Store
"""

import os
import sys
import json
import time
import boto3
from botocore.exceptions import ClientError

# AWS clients
sts_client = boto3.client("sts")
cognito_client = boto3.client("cognito-idp")
iam_client = boto3.client("iam")
lambda_client = boto3.client("lambda")
dynamodb_client = boto3.client("dynamodb")
ssm_client = boto3.client("ssm")

# Get AWS account info
REGION = boto3.session.Session().region_name
ACCOUNT_ID = sts_client.get_caller_identity()["Account"]


def put_ssm_parameter(name: str, value: str, description: str = "") -> None:
    """Store parameter in SSM Parameter Store."""
    try:
        ssm_client.put_parameter(
            Name=name,
            Value=value,
            Type="String",
            Description=description,
            Overwrite=True
        )
        print(f"  ✅ Stored: {name}")
    except Exception as e:
        print(f"  ❌ Failed to store {name}: {e}")
        raise


def create_cognito_user_pool() -> dict:
    """Create Cognito User Pool for Gateway authentication."""
    print("\n📝 Creating Cognito User Pool...")

    pool_name = "customersupport-gateway-pool"

    try:
        # Create User Pool
        response = cognito_client.create_user_pool(
            PoolName=pool_name,
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': False,
                    'RequireLowercase': False,
                    'RequireNumbers': False,
                    'RequireSymbols': False,
                }
            },
            AutoVerifiedAttributes=['email'],
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True,
                }
            ],
        )

        user_pool_id = response['UserPool']['Id']

        print(f"  ✅ User Pool created: {user_pool_id}")

        # Create App Client
        client_response = cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName="customersupport-client",
            ExplicitAuthFlows=[
                'ALLOW_USER_PASSWORD_AUTH',
                'ALLOW_REFRESH_TOKEN_AUTH'
            ],
            GenerateSecret=False,
        )

        client_id = client_response['UserPoolClient']['ClientId']
        print(f"  ✅ App Client created: {client_id}")

        # Create a test user
        username = "testuser"
        password = "TempPass123!"

        try:
            cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                TemporaryPassword=password,
                MessageAction='SUPPRESS',
                UserAttributes=[
                    {'Name': 'email', 'Value': 'test@example.com'},
                    {'Name': 'email_verified', 'Value': 'true'},
                ]
            )

            # Set permanent password
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=username,
                Password=password,
                Permanent=True
            )

            print(f"  ✅ Test user created: {username}")
        except cognito_client.exceptions.UsernameExistsException:
            print(f"  ℹ️  User {username} already exists")

        # Construct discovery URL
        discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"

        # Store in SSM
        put_ssm_parameter(
            "/app/customersupport/agentcore/cognito_user_pool_id",
            user_pool_id,
            "Cognito User Pool ID for Gateway authentication"
        )
        put_ssm_parameter(
            "/app/customersupport/agentcore/machine_client_id",
            client_id,
            "Cognito App Client ID"
        )
        put_ssm_parameter(
            "/app/customersupport/agentcore/cognito_discovery_url",
            discovery_url,
            "Cognito OIDC discovery URL"
        )
        put_ssm_parameter(
            "/app/customersupport/agentcore/cognito_username",
            username,
            "Test user username"
        )
        put_ssm_parameter(
            "/app/customersupport/agentcore/cognito_password",
            password,
            "Test user password"
        )

        return {
            "user_pool_id": user_pool_id,
            "client_id": client_id,
            "discovery_url": discovery_url,
            "username": username,
            "password": password,
        }

    except Exception as e:
        print(f"  ❌ Failed to create Cognito resources: {e}")
        raise


def create_gateway_iam_role() -> str:
    """Create IAM role for Gateway."""
    print("\n🔐 Creating Gateway IAM Role...")

    role_name = "AgentCoreGatewayRole"

    # Trust policy for Gateway
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:customersupport-*"
            }
        ]
    }

    try:
        # Create role
        role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for AgentCore Gateway to invoke Lambda functions"
        )

        role_arn = role_response['Role']['Arn']
        print(f"  ✅ Role created: {role_arn}")

        # Attach inline policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="GatewayLambdaInvokePolicy",
            PolicyDocument=json.dumps(permissions_policy)
        )

        print(f"  ✅ Policy attached to role")

        # Wait for role to be ready
        time.sleep(10)

        # Store in SSM
        put_ssm_parameter(
            "/app/customersupport/agentcore/gateway_iam_role",
            role_arn,
            "IAM Role ARN for Gateway"
        )

        return role_arn

    except iam_client.exceptions.EntityAlreadyExistsException:
        # Role exists, get its ARN
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"  ℹ️  Role already exists: {role_arn}")

        # Store in SSM
        put_ssm_parameter(
            "/app/customersupport/agentcore/gateway_iam_role",
            role_arn,
            "IAM Role ARN for Gateway"
        )

        return role_arn

    except Exception as e:
        print(f"  ❌ Failed to create Gateway IAM role: {e}")
        raise


def create_lambda_iam_role() -> str:
    """Create IAM role for Lambda function."""
    print("\n🔐 Creating Lambda IAM Role...")

    role_name = "AgentCoreLambdaRole"

    # Trust policy
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DescribeTable"
                ],
                "Resource": f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/customersupport-*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameter"
                ],
                "Resource": f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter/app/customersupport/*"
            }
        ]
    }

    try:
        # Create role
        role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for Lambda functions used by AgentCore Gateway"
        )

        role_arn = role_response['Role']['Arn']
        print(f"  ✅ Role created: {role_arn}")

        # Attach inline policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="LambdaExecutionPolicy",
            PolicyDocument=json.dumps(permissions_policy)
        )

        print(f"  ✅ Policy attached to role")

        # Wait for role to be ready
        time.sleep(10)

        # Store in SSM
        put_ssm_parameter(
            "/app/customersupport/agentcore/lambda_iam_role",
            role_arn,
            "IAM Role ARN for Lambda functions"
        )

        return role_arn

    except iam_client.exceptions.EntityAlreadyExistsException:
        role = iam_client.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"  ℹ️  Role already exists: {role_arn}")

        put_ssm_parameter(
            "/app/customersupport/agentcore/lambda_iam_role",
            role_arn,
            "IAM Role ARN for Lambda functions"
        )

        return role_arn

    except Exception as e:
        print(f"  ❌ Failed to create Lambda IAM role: {e}")
        raise


def create_dynamodb_table() -> str:
    """Create DynamoDB table for warranty data."""
    print("\n🗄️  Creating DynamoDB Table...")

    table_name = "customersupport-warranty"

    try:
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'serial_number', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'serial_number', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        print(f"  ✅ Table created: {table_name}")
        print(f"  ⏳ Waiting for table to be active...")

        # Wait for table to be active
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        print(f"  ✅ Table is active")

        # Insert sample data
        print(f"  📝 Inserting sample warranty data...")

        sample_data = [
            {
                'serial_number': {'S': 'MNO33333333'},
                'product_name': {'S': 'Gaming Console Pro'},
                'customer_name': {'S': 'John Doe'},
                'purchase_date': {'S': '2024-01-15'},
                'warranty_end_date': {'S': '2026-01-15'},
                'warranty_type': {'S': 'Extended Warranty'},
                'coverage_details': {'S': 'Full coverage including accidental damage'},
            },
            {
                'serial_number': {'S': 'ABC12345678'},
                'product_name': {'S': 'Laptop Pro 15'},
                'customer_name': {'S': 'Jane Smith'},
                'purchase_date': {'S': '2024-06-01'},
                'warranty_end_date': {'S': '2025-06-01'},
                'warranty_type': {'S': 'Standard Warranty'},
                'coverage_details': {'S': 'Manufacturer defects only'},
            }
        ]

        for item in sample_data:
            dynamodb_client.put_item(TableName=table_name, Item=item)

        print(f"  ✅ Sample data inserted ({len(sample_data)} items)")

        # Store in SSM
        put_ssm_parameter(
            "/app/customersupport/dynamodb/warranty_table_name",
            table_name,
            "DynamoDB table name for warranty data"
        )

        return table_name

    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"  ℹ️  Table already exists: {table_name}")

        put_ssm_parameter(
            "/app/customersupport/dynamodb/warranty_table_name",
            table_name,
            "DynamoDB table name for warranty data"
        )

        return table_name

    except Exception as e:
        print(f"  ❌ Failed to create DynamoDB table: {e}")
        raise


def create_ddgs_layer() -> str:
    """Create DDGS Lambda Layer."""
    print("\n📦 Creating DDGS Lambda Layer...")

    layer_name = "ddgs-layer"

    try:
        # Check if layer already exists
        try:
            layers_response = lambda_client.list_layer_versions(LayerName=layer_name)
            if layers_response.get('LayerVersions'):
                layer_arn = layers_response['LayerVersions'][0]['LayerVersionArn']
                print(f"  ℹ️  Layer already exists: {layer_arn}")
                return layer_arn
        except lambda_client.exceptions.ResourceNotFoundException:
            pass

        # Path to DDGS layer zip file
        layer_zip_path = "../amazon-bedrock-agentcore-samples/01-tutorials/09-AgentCore-E2E/prerequisite/lambda/python/ddgs-layer.zip"

        # Check if file exists
        if not os.path.exists(layer_zip_path):
            print(f"  ⚠️  DDGS layer zip not found at {layer_zip_path}")
            print(f"  ⚠️  Lambda function may fail if it uses web_search tool")
            return None

        # Read layer zip file
        with open(layer_zip_path, 'rb') as f:
            layer_zip = f.read()

        # Create layer
        response = lambda_client.publish_layer_version(
            LayerName=layer_name,
            Description="DuckDuckGo Search library for Python",
            Content={'ZipFile': layer_zip},
            CompatibleRuntimes=['python3.12', 'python3.11', 'python3.10']
        )

        layer_arn = response['LayerVersionArn']
        print(f"  ✅ Layer created: {layer_arn}")
        return layer_arn

    except Exception as e:
        print(f"  ⚠️  Failed to create DDGS layer: {e}")
        print(f"  ⚠️  Lambda function may fail if it uses web_search tool")
        return None


def create_lambda_function(lambda_role_arn: str, layer_arn: str = None) -> str:
    """Create Lambda function placeholder."""
    print("\n⚡ Creating Lambda Function...")

    function_name = "customersupport-gateway-tools"

    # Simple placeholder code
    lambda_code = '''
import json

def lambda_handler(event, context):
    """Placeholder Lambda function."""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Lambda function created. Deploy your actual code.',
            'event': event
        })
    }
'''

    try:
        import zipfile
        import io

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', lambda_code)

        zip_buffer.seek(0)

        # Create function configuration
        function_config = {
            'FunctionName': function_name,
            'Runtime': 'python3.12',
            'Role': lambda_role_arn,
            'Handler': 'lambda_function.lambda_handler',
            'Code': {'ZipFile': zip_buffer.read()},
            'Description': 'Gateway tools for customer support agent',
            'Timeout': 30,
            'MemorySize': 256,
        }

        # Add layer if available
        if layer_arn:
            function_config['Layers'] = [layer_arn]
            print(f"  ℹ️  Attaching DDGS layer to function")

        response = lambda_client.create_function(**function_config)

        function_arn = response['FunctionArn']
        print(f"  ✅ Function created: {function_arn}")
        print(f"  ⚠️  This is a placeholder. Deploy your actual code from src/tools/lambda/")

        # Store in SSM
        put_ssm_parameter(
            "/app/customersupport/agentcore/lambda_arn",
            function_arn,
            "Lambda function ARN for Gateway tools"
        )

        return function_arn

    except lambda_client.exceptions.ResourceConflictException:
        # Function exists, get its ARN
        response = lambda_client.get_function(FunctionName=function_name)
        function_arn = response['Configuration']['FunctionArn']
        print(f"  ℹ️  Function already exists: {function_arn}")

        put_ssm_parameter(
            "/app/customersupport/agentcore/lambda_arn",
            function_arn,
            "Lambda function ARN for Gateway tools"
        )

        return function_arn

    except Exception as e:
        print(f"  ❌ Failed to create Lambda function: {e}")
        raise


def main():
    """Main setup function."""
    print("=" * 70)
    print("🚀 AgentCore Gateway Prerequisites Setup")
    print("=" * 70)
    print(f"\n📍 Region: {REGION}")
    print(f"📍 Account: {ACCOUNT_ID}")

    try:
        # Step 1: Create Cognito User Pool
        cognito_config = create_cognito_user_pool()

        # Step 2: Create Gateway IAM Role
        gateway_role_arn = create_gateway_iam_role()

        # Step 3: Create Lambda IAM Role
        lambda_role_arn = create_lambda_iam_role()

        # Step 4: Create DynamoDB Table
        table_name = create_dynamodb_table()

        # Step 5: Create DDGS Lambda Layer
        layer_arn = create_ddgs_layer()

        # Step 6: Create Lambda Function
        lambda_arn = create_lambda_function(lambda_role_arn, layer_arn)

        # Summary
        print("\n" + "=" * 70)
        print("✅ Prerequisites Setup Complete!")
        print("=" * 70)
        print("\n📊 Created Resources:")
        print(f"\n🔐 Cognito:")
        print(f"   User Pool ID: {cognito_config['user_pool_id']}")
        print(f"   Client ID: {cognito_config['client_id']}")
        print(f"   Test User: {cognito_config['username']}")
        print(f"   Password: {cognito_config['password']}")

        print(f"\n🔐 IAM Roles:")
        print(f"   Gateway Role: {gateway_role_arn}")
        print(f"   Lambda Role: {lambda_role_arn}")

        print(f"\n🗄️  DynamoDB:")
        print(f"   Table: {table_name}")

        print(f"\n⚡ Lambda:")
        print(f"   Function: {lambda_arn}")
        print(f"   ⚠️  Remember to deploy your actual code!")

        print("\n📝 Next Steps:")
        print("   1. Deploy Lambda code: python scripts/deploy_lambda.py")
        print("   2. Setup Gateway: python scripts/setup_gateway.py")
        print("   3. Setup Memory: python scripts/setup_memory.py")
        print("   4. Test Agent: python test_agent_local.py")

    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

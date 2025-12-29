#!/usr/bin/env python3
"""
Deploy Lambda function code from src/tools/lambda/ to AWS.
"""

import io
import sys
import zipfile
from pathlib import Path

import boto3

# AWS clients
ssm_client = boto3.client("ssm")
lambda_client = boto3.client("lambda")


def get_ssm_parameter(name: str) -> str:
    """Get parameter from SSM."""
    try:
        response = ssm_client.get_parameter(Name=name)
        return response["Parameter"]["Value"]
    except Exception as e:
        print(f"❌ Failed to get parameter {name}: {e}")
        raise


def create_lambda_zip() -> bytes:
    """Create ZIP file from src/tools/lambda/ directory."""
    print("\n📦 Creating Lambda deployment package...")

    # Get project root
    project_root = Path(__file__).parent.parent
    lambda_dir = project_root / "src" / "tools" / "lambda"

    if not lambda_dir.exists():
        raise FileNotFoundError(f"Lambda directory not found: {lambda_dir}")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add all Python files from lambda directory
        for py_file in lambda_dir.glob("*.py"):
            if py_file.name != "__init__.py":
                arcname = py_file.name
                zip_file.write(py_file, arcname)
                print(f"  ✅ Added: {arcname}")

    zip_buffer.seek(0)
    zip_content = zip_buffer.read()

    print(f"  📊 Package size: {len(zip_content) / 1024:.2f} KB")
    return zip_content


def update_lambda_function(function_name: str, zip_content: bytes) -> None:
    """Update Lambda function code."""
    print(f"\n⚡ Updating Lambda function: {function_name}")

    try:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )

        print("  ✅ Code updated successfully")
        print(f"  📊 Function ARN: {response['FunctionArn']}")
        print(f"  📊 Runtime: {response['Runtime']}")
        print(f"  📊 Handler: {response['Handler']}")
        print(f"  📊 Code Size: {response['CodeSize'] / 1024:.2f} KB")

    except Exception as e:
        print(f"  ❌ Failed to update function code: {e}")
        raise


def main():
    """Main deployment function."""
    print("=" * 70)
    print("🚀 Deploy Lambda Function Code")
    print("=" * 70)

    try:
        # Get Lambda function ARN from SSM
        lambda_arn = get_ssm_parameter("/app/customersupport/agentcore/lambda_arn")

        # Extract function name from ARN
        # ARN format: arn:aws:lambda:region:account:function:function-name
        function_name = lambda_arn.split(":")[-1]

        print(f"\n📍 Target Function: {function_name}")
        print(f"📍 ARN: {lambda_arn}")

        # Create deployment package
        zip_content = create_lambda_zip()

        # Update function code
        update_lambda_function(function_name, zip_content)

        print("\n" + "=" * 70)
        print("✅ Lambda Deployment Complete!")
        print("=" * 70)
        print("\n📝 Next Steps:")
        print("   1. Test Lambda: aws lambda invoke --function-name {} response.json".format(function_name))
        print("   2. Setup Gateway: python scripts/setup_gateway.py")
        print("   3. Test Agent: python test_agent_local.py")

    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

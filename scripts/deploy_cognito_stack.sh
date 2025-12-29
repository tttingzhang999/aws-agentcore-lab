#!/bin/bash

# Deploy Cognito Stack for AgentCore Gateway

set -e

STACK_NAME="customer-support-cognito"
REGION="ap-northeast-1"

echo "================================="
echo "Deploying Cognito Stack"
echo "================================="

# Deploy CloudFormation stack
echo ""
echo "📦 Deploying CloudFormation stack: $STACK_NAME"
aws cloudformation deploy \
  --template-file prerequisite/cognito-stack.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --region $REGION \
  --no-fail-on-empty-changeset

# Get stack outputs
echo ""
echo "✅ Stack deployed successfully!"
echo ""
echo "📊 Stack Outputs:"
aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs' \
  --output table

echo ""
echo "✅ Cognito configuration complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Run: aws-vault exec gc-playground -- ./scripts/setup_gateway.sh"
echo "   2. Test: aws-vault exec gc-playground -- uv run python test_agent_local.py"

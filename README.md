# AgentCore Agent Test - Lab 3: Scale with Gateway and Identity

[Reference Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/850fcd5c-fd1f-48d7-932c-ad9babede979/en-US/50-add-tool-gateway/)

## Setup Instructions

### Step 1: One-Time Memory Setup ⚠️

**Only need to do this ONCE per environment!**

This creates your AgentCore Memory resource with multiple strategies:

```bash
# Make sure AWS credentials are configured
export AWS_REGION=ap-northeast-1  # or your preferred region

# Run the one-time setup script
aws-vault exec {your-aws-profile} -- uv run python scripts/setup_memory.py
```

The script will:

1. Create AgentCore Memory resource (takes ~2 minutes)
2. Configure USER_PREFERENCE and SEMANTIC strategies
3. Display your Memory ID
4. Optionally seed sample customer history

**Save the Memory ID!** Add it to your `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Memory ID
# AGENTCORE_MEMORY_ID=your-memory-id-from-setup
```

### Step 2: Configure Environment

```bash
# .env file should contain:
AWS_REGION=us-east-1
AGENTCORE_MEMORY_ID=your-memory-id-here
```

**Note**: The Memory ID persists across deployments. You don't need to run the setup script again unless you're starting in a new AWS environment.

---

## Running the Agent

### Test Locally

```bash
# Make sure .env is configured with AGENTCORE_MEMORY_ID
aws-vault exec {your-aws-profile} -- uv run test_agent_local.py
```

**Test Menu:**

```text
🎯 AgentCore Customer Support Agent - 本地測試

選擇測試模式:

1. 測試工具函式
2. 測試 Agent 對話 (with Memory!)
3. 測試 Agent 串流回應 (with Memory!)
4. 互動模式 (與 Agent 對話)
5. 執行所有測試

請選擇 (1-5):
```

## Test prompt

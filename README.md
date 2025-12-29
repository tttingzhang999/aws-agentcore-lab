# AgentCore Agent Test - Lab 2: Add Memory

Transform your customer support agent with persistent memory capabilities!

[Reference Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/850fcd5c-fd1f-48d7-932c-ad9babede979/en-US/30-add-memory/)

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

---

## How It Works

### Memory Hooks Architecture

The agent uses Strands Hooks to automatically manage memory:

1. **Before responding** (`retrieve_customer_context`):

   - Retrieves relevant customer context from memory
   - Injects context into the conversation
   - Enables personalized responses

2. **After responding** (`save_support_interaction`):
   - Saves the conversation to memory
   - Extracts preferences and facts
   - Updates long-term memory

### Customer Identification

You can pass a `customer_id` in your payload:

```python
payload = {
    "prompt": "What's my order status?",
    "customer_id": "test_customer_001"  # Optional: defaults to session_id
}
```

Without a `customer_id`, the agent uses the session ID to track context within a session.

---

## Key Concepts

### One-Time Setup vs Regular Use

| Task                   | Frequency                           | Command                                 |
| ---------------------- | ----------------------------------- | --------------------------------------- |
| Create Memory Resource | **ONCE per environment**            | `uv run python scripts/setup_memory.py` |
| Configure .env         | **ONCE** (unless Memory ID changes) | `cp .env.example .env` and edit         |
| Run Agent              | **Every time**                      | `uv run test_agent_local.py`            |

### Memory Strategies

- **USER_PREFERENCE**: Learns customer preferences automatically

  - Communication preferences (email, SMS)
  - Product preferences (brands, models)
  - Behavioral patterns

- **SEMANTIC**: Stores factual information
  - Order numbers and purchase history
  - Product information and warranties
  - Support ticket details

### Namespace Pattern

Memories are organized by customer:

```
support/customer/{customer_id}/preferences
support/customer/{customer_id}/semantic
```

This ensures customer data isolation and efficient retrieval.

## Test prompt

- question:

  - round 1
    - i have bought a samsung galaxy s22, order number is #abc12345
  - round 2
    - what is the order number of my recent bought smartphone?

- response:
  agent 會使用 tool 去尋找這個商品的資料(記憶有儲存 "samsung galaxy s22" 的資料)，輸出商品信息，但看起來不會紀錄訂單資料

- 是否需要在 prompt 下訂單編號相關資訊？
- 是否需要有一個 tool for order number

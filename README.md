# Customer Support Agent with AgentCore Gateway

完整的客服 Agent 實作，整合 Amazon Bedrock AgentCore 的核心功能：

- **Memory**: 記憶客戶對話歷史和偏好
- **Gateway**: 透過 MCP 共享可重用的工具
- **Identity**: 使用 Cognito OAuth 保護 Gateway 存取

[Reference Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/850fcd5c-fd1f-48d7-932c-ad9babede979/en-US/50-add-tool-gateway/)

## 專案架構

### 核心功能

本專案實作了一個完整的企業級客服 Agent，包含：

1. **本地工具** - Agent 專屬的領域知識

   - `get_product_info()`: 產品資訊查詢
   - `get_return_policy()`: 退貨政策
   - `get_technical_support()`: 技術支援指南

2. **Gateway 共享工具** - 可跨多個 Agent 重用

   - `check_warranty_status()`: 查詢產品保固（連接 DynamoDB）
   - `web_search()`: 網路搜尋（DuckDuckGo）

3. **記憶管理** - 個人化的客戶體驗

   - Semantic Memory: 自動儲存對話內容
   - Summary Memory: 總結客戶偏好

4. **安全認證** - 企業級存取控制
   - Cognito OAuth/JWT 認證
   - IAM-based 資源存取

### 架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Support Agent                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Local Tools (Agent-Specific)             │  │
│  │  • get_product_info()                                 │  │
│  │  • get_return_policy()                                │  │
│  │  • get_technical_support()                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                             ↓                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │             MCP Client (Strands SDK)                  │  │
│  │  • OAuth Token Authentication                         │  │
│  │  • Connects to AgentCore Gateway                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             ↓
                   (JWT Bearer Token)
                             ↓
┌─────────────────────────────────────────────────────────────┐
│              AgentCore Gateway (MCP Server)                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │           Inbound Auth (Cognito)                      │  │
│  │  • Validates JWT Token                                │  │
│  │  • Checks Client ID                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                             ↓                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │        Lambda Target (Shared Tools)                   │  │
│  │  • check_warranty_status()                            │  │
│  │  • web_search()                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                             ↓                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │    Outbound Auth (IAM Role)                           │  │
│  │  • Invokes Lambda Function                            │  │
│  │  • Accesses DynamoDB (Warranty Data)                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 關鍵組件說明

#### 1. AgentCore Gateway

- **作用**: 將 Lambda 函數轉換為標準 MCP 工具
- **優勢**:
  - 多個 Agent 可共享同一工具端點
  - 集中管理工具定義和版本
  - 統一的安全控制

#### 2. Inbound Authentication (Cognito)

- **作用**: 驗證呼叫 Gateway 的 Agent 身份
- **流程**:
  1. Agent 向 Cognito 請求 JWT Token
  2. 每次呼叫 Gateway 時附帶 Token
  3. Gateway 驗證 Token 的有效性和 Client ID

#### 3. Outbound Authentication (IAM)

- **作用**: Gateway 存取後端資源時的身份驗證
- **範例**:
  - Lambda 呼叫 DynamoDB 查詢保固資料
  - 使用 Gateway IAM Role 授權

#### 4. Lambda Tools

- `check_warranty_status()`: 查詢產品保固狀態（來自 DynamoDB）
- `web_search()`: 使用 DuckDuckGo 進行網路搜尋

## 快速開始

### 完整設定（從零開始）

```bash
# 1. 安裝依賴
uv sync

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env，設定 AWS_REGION

# 3. 部署 Cognito 基礎設施（CloudFormation）- 只需執行一次
aws-vault exec {profile} -- bash scripts/deploy_cognito_stack.sh

# 4. 部署其他 AWS 資源（DynamoDB, Lambda, IAM）- 只需執行一次
aws-vault exec {profile} -- uv run python scripts/setup_prerequisites.py

# 5. 部署 Lambda 程式碼
aws-vault exec {profile} -- uv run python scripts/deploy_lambda.py

# 6. 設定 Gateway（只需執行一次）
aws-vault exec {profile} -- uv run python scripts/setup_gateway.py

# 7. 設定 Memory（只需執行一次）
aws-vault exec {profile} -- uv run python scripts/setup_memory.py

# 8. 測試 Agent
aws-vault exec {profile} -- uv run python test_agent_local.py
```

### 方法 2: 使用 Workshop 環境

如果你在 AWS Workshop 環境中（已有 CloudFormation 建立的資源）：

```bash
# 1-2. 同上
# 3. 跳過（已由 CloudFormation 建立）
# 4. 跳過（已部署）
# 5-7. 繼續執行
```

## 詳細設定說明

### Step 0: 部署 Cognito 基礎設施 (CloudFormation)

**使用 CloudFormation 部署 Cognito 認證系統**

```bash
aws-vault exec {profile} -- bash scripts/deploy_cognito_stack.sh
```

**建立的資源：**

1. **Cognito User Pool** - OAuth2 Client Credentials 認證

   - User Pool（Machine-to-Machine 認證）
   - App Client（使用 client_secret）
   - Resource Server（定義 OAuth scope）
   - User Pool Domain（OAuth endpoints）

2. **SSM Parameters** - 自動儲存配置
   - `/app/customersupport/agentcore/machine_client_id`
   - `/app/customersupport/agentcore/machine_client_secret`
   - `/app/customersupport/agentcore/cognito_user_pool_id`
   - `/app/customersupport/agentcore/cognito_discovery_url`
   - `/app/customersupport/agentcore/cognito_token_url`
   - `/app/customersupport/agentcore/cognito_domain`
   - `/app/customersupport/agentcore/cognito_auth_scope`

**輸出範例：**

```
✅ Stack deployed successfully!

📊 Stack Outputs:
   User Pool ID: ap-northeast-1_xxxxx
   Machine Client ID: xxxxxxxxxxxxx
   Cognito Domain: https://customersupport-{account-id}.auth.{region}.amazoncognito.com
   Token Endpoint: https://customersupport-{account-id}.auth.{region}.amazoncognito.com/oauth2/token
```

### Step 1: 建立其他 AWS 資源 (setup_prerequisites.py)

**建立 DynamoDB, Lambda, IAM 資源**

```bash
aws-vault exec {profile} -- uv run python scripts/setup_prerequisites.py
```

**建立的資源：**

1. **IAM Roles**

   - Gateway IAM Role - 讓 Gateway 可以呼叫 Lambda
   - Lambda IAM Role - 讓 Lambda 可以存取 DynamoDB 和 CloudWatch

2. **DynamoDB Table** - 儲存保固資料

   - Table: `customersupport-warranty`
   - 自動插入範例資料

3. **Lambda Function** (佔位)
   - Function: `customersupport-gateway-tools`
   - 需要後續部署實際程式碼

**輸出範例：**

```
✅ Prerequisites Setup Complete!

📊 Created Resources:

🔐 IAM Roles:
   Gateway Role: arn:aws:iam::xxxx:role/AgentCoreGatewayRole
   Lambda Role: arn:aws:iam::xxxx:role/AgentCoreLambdaRole

🗄️  DynamoDB:
   Table: customersupport-warranty

⚡ Lambda:
   Function: arn:aws:lambda:ap-northeast-1:xxxx:function:customersupport-gateway-tools
```

### Step 2: 部署 Lambda 程式碼 (deploy_lambda.py)

**將 src/tools/lambda/ 的程式碼部署到 AWS Lambda**

```bash
aws-vault exec {profile} -- uv run python scripts/deploy_lambda.py
```

**功能：**

- 打包 `src/tools/lambda/` 目錄中的所有 Python 檔案
- 上傳到 Lambda function
- 包含：
  - `lambda_function.py` - Handler（路由工具呼叫）
  - `check_warranty.py` - 保固查詢邏輯
  - `web_search.py` - 網路搜尋邏輯

### Step 3: 設定 AgentCore Gateway (setup_gateway.py)

**建立 Gateway 並註冊 Lambda 工具**

```bash
aws-vault exec {profile} -- uv run python scripts/setup_gateway.py
```

**功能：**

1. 建立 AgentCore Gateway（使用 Cognito 認證）
2. 將 Lambda 註冊為 Gateway Target
3. 載入工具定義（從 `prerequisite/lambda/api_spec.json`）
4. 儲存 Gateway 配置到 SSM

### Step 4: 設定 AgentCore Memory (setup_memory.py)

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

## Lab 3 重點實作說明

### 1. Lambda Function Handler (`src/tools/lambda/lambda_function.py`)

此 Lambda 函數作為 Gateway Target，負責處理工具呼叫：

```python
def lambda_handler(event, context):
    # Gateway 會在 context 中傳遞工具名稱
    extended_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
    resource = extended_tool_name.split("___")[1]  # 提取工具名稱

    if resource == "check_warranty_status":
        serial_number = get_named_parameter(event=event, name="serial_number")
        customer_email = get_named_parameter(event=event, name="customer_email")

        warranty_status = check_warranty_status(serial_number, customer_email)
        return {"statusCode": 200, "body": warranty_status}

    elif resource == "web_search":
        keywords = get_named_parameter(event=event, name="keywords")
        region = get_named_parameter(event=event, name="region") or "us-en"
        max_results = get_named_parameter(event=event, name="max_results") or 5

        search_results = web_search(keywords, region, int(max_results))
        return {"statusCode": 200, "body": search_results}
```

**關鍵點**:

- Gateway 透過 `context.client_context.custom["bedrockAgentCoreToolName"]` 傳遞工具名稱
- `event` 包含工具參數 (如 `serial_number`, `keywords`)
- 一個 Lambda 可以處理多個工具

### 2. Tool Schema Definition (`prerequisite/lambda/api_spec.json`)

定義 Gateway 提供的工具接口：

```json
[
  {
    "name": "check_warranty_status",
    "description": "Check the warranty status of a product...",
    "inputSchema": {
      "type": "object",
      "properties": {
        "serial_number": { "type": "string" },
        "customer_email": { "type": "string" }
      },
      "required": ["serial_number"]
    }
  },
  {
    "name": "web_search",
    "description": "Search the web for updated information...",
    "inputSchema": {
      "type": "object",
      "properties": {
        "keywords": { "type": "string" },
        "region": { "type": "string" },
        "max_results": { "type": "integer" }
      },
      "required": ["keywords"]
    }
  }
]
```

**關鍵點**:

- 遵循 OpenAPI 規範定義工具
- `inputSchema` 描述工具參數的型別和必填性
- Agent 會根據此定義自動生成工具呼叫

### 3. MCP Client Integration (`src/main.py`)

Agent 透過 MCP Client 連接 Gateway（使用 OAuth2 Client Credentials）：

```python
def get_mcp_client():
    """Get MCP client connected to AgentCore Gateway."""
    # 從 SSM 取得 Gateway URL
    gateway_url = get_ssm_parameter("/app/customersupport/agentcore/gateway_url")

    # 建立 transport callable，每次調用時獲取新 token
    def create_transport():
        # 使用 OAuth2 client_credentials flow 取得 access token
        cognito_config = get_or_create_cognito_pool(refresh_token=True)
        bearer_token = cognito_config["bearer_token"]

        # 建立 httpx 客戶端並附帶認證
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=30.0,
        )

        return streamable_http_client(gateway_url, http_client=http_client)

    # 建立 MCP 客戶端
    mcp_client = MCPClient(create_transport)
    return mcp_client

# 在 Agent 中使用
mcp_client = get_mcp_client()
with mcp_client as client:
    gateway_tools = client.list_tools_sync()  # 取得 Gateway 工具
    all_tools = local_tools + gateway_tools    # 合併本地和 Gateway 工具

    agent = Agent(model=model, tools=all_tools, ...)
```

**關鍵點**:

- 使用 OAuth2 Client Credentials 獲取 access token
- 每次調用時獲取新 token（避免 token 過期）
- 通過 httpx.AsyncClient 傳遞認證頭
- MCP Client 自動處理工具發現和呼叫
- 可以混合使用本地工具和 Gateway 工具

### 4. Authentication Flow

完整的 OAuth2 Client Credentials 認證流程：

```
1. Agent 啟動
   ↓
2. 向 Cognito Token Endpoint 發送請求
   - grant_type=client_credentials
   - Authorization: Basic {base64(client_id:client_secret)}
   - scope=customersupport-resource-server-{stack}/read
   ↓
3. Cognito 返回 access token
   - token_use=access（不是 id token）
   - 包含正確的 scope
   ↓
4. 建立 MCP Client（附帶 access token）
   ↓
5. Agent 需要使用工具
   ↓
6. MCP Client 呼叫 Gateway（附帶 Bearer Token）
   ↓
7. Gateway JWT Authorizer 驗證 Token
   - 檢查 issuer（Cognito User Pool）
   - 檢查 audience（client_id）
   - 檢查 scope
   - 驗證簽名（使用 JWKS）
   ├─ ✅ Valid → 繼續
   └─ ❌ Invalid → 401 Unauthorized
   ↓
8. Gateway 使用 IAM Role 呼叫 Lambda
   ↓
9. Lambda 執行工具邏輯
   ↓
10. 結果返回給 Agent
```

## 測試 Gateway 整合

### 測試保固查詢工具

```python
# 在互動模式中測試
"I have a Gaming Console Pro device, I want to check my warranty status,
warranty serial number is MNO33333333."
```

Agent 會：

1. 識別需要使用 `check_warranty_status` 工具
2. 透過 MCP Client 呼叫 Gateway
3. Gateway 驗證身份後呼叫 Lambda
4. Lambda 查詢 DynamoDB 並返回保固資訊

### 測試網路搜尋工具

```python
"Tell me detailed information about the technical documentation on installing a new CPU"
```

Agent 會：

1. 使用 `web_search` 工具搜尋相關資訊
2. 透過 Gateway 呼叫 Lambda 中的 DuckDuckGo 搜尋
3. 整合搜尋結果並回答用戶問題

## 專案結構

```
agentcoreAgentTest/
├── src/
│   ├── main.py                      # Agent 主程式
│   ├── memory/
│   │   └── client.py                # Memory 整合
│   ├── model/
│   │   └── load.py                  # 模型載入
│   ├── tools/                       # 工具目錄
│   │   ├── lambda/                  # Gateway Lambda 工具（部署到 AWS）
│   │   │   ├── lambda_function.py  # Lambda Handler
│   │   │   ├── check_warranty.py   # 保固查詢邏輯
│   │   │   └── web_search.py       # 網路搜尋邏輯
│   │   ├── add_numbers.py          # 本地工具
│   │   ├── get_product_info.py     # 本地工具
│   │   ├── get_return_policy.py    # 本地工具
│   │   └── get_technical_support.py # 本地工具
│   └── utils/
│       └── aws_helpers.py          # AWS 工具函數（SSM, Cognito）
├── prerequisite/
│   └── lambda/
│       └── api_spec.json           # MCP 工具定義 Schema
├── scripts/
│   ├── setup_memory.py             # Memory 設定腳本
│   └── setup_gateway.py            # Gateway 設定腳本
└── README.md
```

### 關鍵檔案說明

- **`src/main.py`**: Agent 主程式，整合所有功能
- **`src/tools/lambda/`**: 部署到 AWS Lambda 的工具（與本地工具分離）
- **`src/utils/aws_helpers.py`**: AWS 服務輔助函數
- **`prerequisite/lambda/api_spec.json`**: MCP 工具的 OpenAPI 定義

> 💡 **為什麼 Lambda 工具要分開？**
> 詳見 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解本地工具 vs Lambda 工具的設計考量

## 常見問題

### Q: Gateway 和本地工具的差異？

**本地工具**:

- 直接在 Agent 程式中定義
- 只能被當前 Agent 使用
- 修改需要重新部署 Agent

**Gateway 工具**:

- 在 Lambda 中實作，透過 Gateway 暴露
- 多個 Agent 可共享
- 可獨立更新，不影響 Agent
- 統一的安全控制

### Q: 為什麼要使用 Cognito OAuth2 Client Credentials？

1. **Machine-to-Machine 認證**: 專為服務間通訊設計，不需要用戶互動
2. **安全性**: 只有持有 client_secret 的 Agent 可以呼叫 Gateway
3. **標準化**: OAuth2 是 MCP 和 API 的標準認證方式
4. **審計**: 可追蹤哪個 Agent（client_id）使用了哪些工具
5. **Access Token vs ID Token**: Gateway 需要 access token（包含 scope），而不是 ID token

### Q: 為什麼不能用 USER_PASSWORD_AUTH？

USER_PASSWORD_AUTH 返回的是 ID token，用於識別用戶身份。Gateway JWT Authorizer 需要的是：
- **Access Token**: 包含 scope 和 resource server 信息
- **Client Credentials Flow**: 專為服務間認證設計
- **Resource Server**: 定義 Agent 可以訪問的資源範圍

### Q: 如何新增更多工具到 Gateway？

1. 在 Lambda 中實作工具邏輯
2. 更新 `prerequisite/lambda/api_spec.json` 加入工具定義
3. 重新執行 `scripts/setup_gateway.py`

## Test prompt

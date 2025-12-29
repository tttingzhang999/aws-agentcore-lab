# 設定腳本說明

本目錄包含所有設定 AgentCore 環境所需的腳本。

## 腳本執行順序

```
1. setup_prerequisites.py   # 建立 AWS 基礎設施
   ↓
2. deploy_lambda.py         # 部署 Lambda 程式碼
   ↓
3. setup_gateway.py         # 設定 AgentCore Gateway
   ↓
4. setup_memory.py          # 設定 AgentCore Memory
   ↓
5. 測試 Agent
```

## 詳細說明

### 1. setup_prerequisites.py

**目的**: 建立所有必要的 AWS 資源

**建立的資源**:
- ✅ Cognito User Pool（OAuth 認證）
- ✅ IAM Roles（Gateway + Lambda）
- ✅ DynamoDB Table（保固資料）
- ✅ Lambda Function（佔位）

**執行**:
```bash
aws-vault exec {profile} -- uv run python scripts/setup_prerequisites.py
```

**輸出**: 所有資源的 ARN 和 ID 會儲存到 SSM Parameter Store

**儲存的 SSM 參數**:
```
/app/customersupport/agentcore/cognito_user_pool_id
/app/customersupport/agentcore/machine_client_id
/app/customersupport/agentcore/cognito_discovery_url
/app/customersupport/agentcore/cognito_username
/app/customersupport/agentcore/cognito_password
/app/customersupport/agentcore/gateway_iam_role
/app/customersupport/agentcore/lambda_iam_role
/app/customersupport/agentcore/lambda_arn
/app/customersupport/dynamodb/warranty_table_name
```

**冪等性**: ✅ 可以重複執行，已存在的資源會被重用

---

### 2. deploy_lambda.py

**目的**: 將本地的 Lambda 程式碼部署到 AWS

**部署的檔案**:
```
src/tools/lambda/
├── lambda_function.py  # Handler（工具路由）
├── check_warranty.py   # 保固查詢
└── web_search.py       # 網路搜尋
```

**執行**:
```bash
aws-vault exec {profile} -- uv run python scripts/deploy_lambda.py
```

**流程**:
1. 從 SSM 取得 Lambda Function ARN
2. 打包 `src/tools/lambda/` 所有 `.py` 檔案
3. 上傳 ZIP 到 Lambda
4. 更新 Function Code

**何時執行**:
- 第一次設定
- 修改 Lambda 程式碼後

---

### 3. setup_gateway.py

**目的**: 建立 AgentCore Gateway 並註冊工具

**執行**:
```bash
aws-vault exec {profile} -- uv run python scripts/setup_gateway.py
```

**流程**:
1. 建立 Gateway（如果不存在）
   - 使用 Cognito JWT 認證
   - 使用 Gateway IAM Role
2. 載入工具定義（`prerequisite/lambda/api_spec.json`）
3. 建立 Lambda Target
4. 儲存 Gateway URL 到 SSM

**建立的工具**:
- `check_warranty_status` - 查詢保固
- `web_search` - 網路搜尋

**儲存的 SSM 參數**:
```
/app/customersupport/agentcore/gateway_id
/app/customersupport/agentcore/gateway_name
/app/customersupport/agentcore/gateway_arn
/app/customersupport/agentcore/gateway_url
```

---

### 4. setup_memory.py

**目的**: 建立 AgentCore Memory 資源

**執行**:
```bash
aws-vault exec {profile} -- uv run python scripts/setup_memory.py
```

**建立的 Memory Strategies**:
- Semantic Memory - 儲存對話內容
- Summary Memory - 總結客戶偏好

**儲存的 SSM 參數**:
```
/app/customersupport/agentcore/memory_id
```

**注意**: 只需執行一次，Memory ID 會持續使用

---

## 故障排除

### 問題: "Parameter not found"

**原因**: SSM Parameter Store 沒有必要的參數

**解決**: 執行 `setup_prerequisites.py` 建立所有資源

### 問題: "Role already exists"

**原因**: IAM Role 已經存在

**解決**: 腳本會自動重用現有 Role，不影響執行

### 問題: Lambda 部署失敗

**檢查**:
1. Lambda IAM Role 是否存在
2. `src/tools/lambda/` 目錄是否有程式碼
3. 檔案權限是否正確

### 問題: Gateway 建立失敗

**檢查**:
1. Cognito User Pool 是否建立
2. Gateway IAM Role 是否存在
3. Lambda Function 是否已部署

---

## 清理資源

如果需要重新開始，可以手動刪除資源：

```bash
# 刪除 Gateway
aws bedrock-agentcore-control delete-gateway --gateway-identifier <gateway-id>

# 刪除 Lambda
aws lambda delete-function --function-name customersupport-gateway-tools

# 刪除 DynamoDB Table
aws dynamodb delete-table --table-name customersupport-warranty

# 刪除 IAM Roles
aws iam delete-role-policy --role-name AgentCoreGatewayRole --policy-name GatewayLambdaInvokePolicy
aws iam delete-role --role-name AgentCoreGatewayRole

aws iam delete-role-policy --role-name AgentCoreLambdaRole --policy-name LambdaExecutionPolicy
aws iam delete-role --role-name AgentCoreLambdaRole

# 刪除 Cognito User Pool
aws cognito-idp delete-user-pool --user-pool-id <user-pool-id>

# 刪除 SSM Parameters
aws ssm delete-parameters --names \
  /app/customersupport/agentcore/cognito_user_pool_id \
  /app/customersupport/agentcore/machine_client_id \
  /app/customersupport/agentcore/cognito_discovery_url \
  # ... (其他參數)
```

---

## 最佳實踐

1. **執行順序**: 嚴格按照 1→2→3→4 的順序執行
2. **檢查輸出**: 每個腳本都會顯示詳細的執行結果
3. **保存憑證**: Cognito 測試用戶的密碼會顯示在輸出中
4. **SSM 優先**: 所有配置都儲存在 SSM，不需要手動記錄
5. **冪等執行**: 腳本可以安全地重複執行

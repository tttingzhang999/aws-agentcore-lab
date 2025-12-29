"""
Streamlit 聊天界面 - 連接到 AgentCore 部署的 Agent

使用方式:
1. 先部署 Agent: agentcore deploy
2. 取得 agent_arn: agentcore status
3. 更新下方的 AGENT_ARN
4. 執行: streamlit run streamlit_app.py
"""

import json
import re
import uuid

import boto3
import streamlit as st

# ==================== 設定 ====================
# 從 `agentcore status` 取得
AGENT_ARN = "arn:aws:bedrock-agentcore:ap-northeast-1:593713876380:runtime/agentcoreAgentTest_Agent-ofKqnH82cq"
AWS_REGION = "ap-northeast-1"

# ==================== 初始化 ====================
st.set_page_config(page_title="AgentCore Chatbot", page_icon="🤖", layout="centered")


# 初始化 BedrockAgentCore client
@st.cache_resource
def get_client():
    return boto3.client("bedrock-agentcore", region_name=AWS_REGION)


client = get_client()


def process_event_stream(response):
    """處理 AWS EventStream 回應並合併為完整文字"""
    result_text = ""

    if "response" in response:
        event_stream = response["response"]

        # 迭代 EventStream
        for event in event_stream:
            # Debug: 顯示事件類型和內容
            st.write(f"Event type: {type(event)}")
            st.write(f"Event content: {event}")

            # 處理字典事件（如 {"data": "text"}）
            if isinstance(event, dict):
                if "data" in event and isinstance(event["data"], str):
                    result_text += event["data"]
                else:
                    # 其他字典事件，可能包含元數據
                    st.write(f"Dict event without 'data': {event}")
            # 處理 bytes
            elif isinstance(event, bytes):
                try:
                    decoded = event.decode("utf-8")
                    if decoded.startswith('"') and decoded.endswith('"'):
                        decoded = json.loads(decoded)
                    result_text += decoded
                except (UnicodeDecodeError, json.JSONDecodeError):
                    result_text += str(event)
            # 處理字串
            elif isinstance(event, str):
                result_text += event

    # 移除 <thinking> 標籤及其內容
    result_text = re.sub(r"<thinking>.*?</thinking>", "", result_text, flags=re.DOTALL)
    # 清理多餘的空白
    result_text = result_text.strip()

    return result_text


# ==================== UI ====================
st.title("🤖 AgentCore Chatbot")
st.caption("由 Amazon Bedrock AgentCore 提供支援")

# 側邊欄設定
with st.sidebar:
    st.header("⚙️ 設定")
    st.info(f"**Agent ARN:**\n`{AGENT_ARN}`")
    st.info(f"**Region:** {AWS_REGION}")

    if st.button("🗑️ 清除對話"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
        ### 💡 試試這些提示詞：
        - "幫我計算 123 + 456"
        - "用 Python 生成費氏數列"
        - "解釋什麼是機器學習"
        - "畫一個 sin/cos 圖表"
        """
    )

# 初始化聊天歷史
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 你好！我是 AgentCore Agent。我可以幫你執行程式碼、回答問題、使用各種工具。有什麼我能幫忙的嗎？",
        }
    ]

# 顯示聊天歷史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 使用者輸入
if prompt := st.chat_input("輸入你的訊息..."):
    # 加入使用者訊息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Agent 回應
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        try:
            # 呼叫 AgentCore
            with st.spinner("🤔 思考中..."):
                session_id = st.session_state.get("session_id")
                if not session_id:
                    session_id = str(uuid.uuid4())
                    st.session_state["session_id"] = session_id

                response = client.invoke_agent_runtime(
                    agentRuntimeArn=AGENT_ARN,
                    qualifier="DEFAULT",
                    runtimeSessionId=session_id,
                    payload=json.dumps({"prompt": prompt}),
                )

            # 處理 EventStream 回應
            answer = process_event_stream(response)

            # 如果還是空的，顯示錯誤
            if not answer or answer.strip() == "":
                answer = "⚠️ Agent 沒有回傳內容。請檢查 Agent 是否正常運作。"
                # Debug: 顯示原始回應
                with st.expander("🔍 Debug - 原始回應"):
                    st.json(str(response))

            message_placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            error_msg = (
                f"❌ 錯誤: {str(e)}\n\n"
                "請確認:\n"
                "1. Agent 已部署 (`agentcore deploy`)\n"
                "2. AGENT_ARN 設定正確\n"
                "3. AWS 認證有效"
            )
            message_placeholder.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )

# 頁尾
st.markdown("---")
st.caption("Made with ❤️ using Amazon Bedrock AgentCore")

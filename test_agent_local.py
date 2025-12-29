"""
本地測試腳本 - 不需要部署到 AgentCore 即可測試 Agent 和工具

使用方式:
    python test_agent_local.py
"""

import asyncio

from model.load import load_model
from strands import Agent
from tools.add_numbers import add_numbers
from tools.get_product_info import get_product_info
from tools.get_return_policy import get_return_policy
from tools.get_technical_support import get_technical_support
from tools.web_search import web_search

# System prompt
system_prompt = """You are a helpful and professional customer support assistant for an e-commerce company.
Your role is to:
- Provide accurate information using the tools available to you
- Be friendly, patient, and understanding with customers
- Always offer additional help after answering questions
- If you can't help with something, direct customers to the appropriate contact

You have access to the following tools:
1. get_return_policy() - For return policy questions
2. get_product_info() - To get information about a specific product
3. web_search() - Search the web for troubleshooting help
4. get_technical_support() - For technical support issues

Always use the appropriate tool to get accurate, up-to-date information rather than guessing."""


def test_tools():
    """測試所有工具函式是否正常運作"""
    print("=" * 80)
    print("🧪 測試工具函式")
    print("=" * 80)

    # Test 1: get_return_policy
    print("\n📋 Test 1: get_return_policy('smartphones')")
    print("-" * 80)
    result = get_return_policy("smartphones")
    print(result)

    # Test 2: get_product_info
    print("\n📦 Test 2: get_product_info('Samsung Galaxy S22')")
    print("-" * 80)
    result = get_product_info("Samsung Galaxy S22")
    print(result)

    # Test 3: web_search
    print("\n🔍 Test 3: web_search('iphone 14 battery life')")
    print("-" * 80)
    result = web_search("iphone 14 battery life")
    print(result)

    # Test 4: get_technical_support
    print("\n🔧 Test 4: get_technical_support('phone won\\'t turn on')")
    print("-" * 80)
    result = get_technical_support("phone won't turn on")
    print(result)

    # Test 5: add_numbers
    print("\n🔢 Test 5: add_numbers(123, 456)")
    print("-" * 80)
    result = add_numbers(123, 456)
    print(f"Result: {result}")


async def test_agent():
    """測試 Agent 完整對話流程"""
    print("\n" + "=" * 80)
    print("🤖 測試 Agent 對話")
    print("=" * 80)

    # 創建 Agent
    agent = Agent(
        model=load_model(),
        system_prompt=system_prompt,
        tools=[
            get_return_policy,
            get_product_info,
            web_search,
            get_technical_support,
            add_numbers,
        ],
    )

    # 測試場景
    test_queries = [
        "What's the return policy for my Samsung Galaxy S22?",
        "Tell me about the iPhone 14",
        "My phone won't turn on, what should I do?",
        "Calculate 123 + 456",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n💬 Test Query {i}:")
        print(f"Customer: {query}")
        print("-" * 80)

        # 同步調用
        response = agent(query)
        print(f"Agent: {response}")
        print()


async def test_agent_streaming():
    """測試 Agent 串流回應"""
    print("\n" + "=" * 80)
    print("🌊 測試 Agent 串流回應")
    print("=" * 80)

    agent = Agent(
        model=load_model(),
        system_prompt=system_prompt,
        tools=[
            get_return_policy,
            get_product_info,
            web_search,
            get_technical_support,
        ],
    )

    query = "What's the return policy for laptops and tell me about MacBook Pro 14?"
    print(f"\n💬 Query: {query}")
    print("-" * 80)
    print("Agent (streaming): ", end="", flush=True)

    # 異步串流
    async for chunk in agent.stream_async(query):
        if "data" in chunk and isinstance(chunk["data"], str):
            print(chunk["data"], end="", flush=True)

    print("\n")


def interactive_mode():
    """互動模式 - 可以與 Agent 對話"""
    print("\n" + "=" * 80)
    print("💬 互動模式 (輸入 'quit' 或 'exit' 結束)")
    print("=" * 80)

    agent = Agent(
        model=load_model(),
        system_prompt=system_prompt,
        tools=[
            get_return_policy,
            get_product_info,
            web_search,
            get_technical_support,
            add_numbers,
        ],
    )

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            print("🤖 Agent: ", end="", flush=True)
            response = agent(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """主測試流程"""
    print("\n🎯 AgentCore Customer Support Agent - 本地測試")
    print("=" * 80)

    # 選擇測試模式
    print("\n選擇測試模式:")
    print("1. 測試工具函式")
    print("2. 測試 Agent 對話")
    print("3. 測試 Agent 串流回應")
    print("4. 互動模式 (與 Agent 對話)")
    print("5. 執行所有測試")

    choice = input("\n請選擇 (1-5): ").strip()

    if choice == "1":
        test_tools()
    elif choice == "2":
        asyncio.run(test_agent())
    elif choice == "3":
        asyncio.run(test_agent_streaming())
    elif choice == "4":
        interactive_mode()
    elif choice == "5":
        test_tools()
        asyncio.run(test_agent())
        asyncio.run(test_agent_streaming())
    else:
        print("❌ 無效的選擇")


if __name__ == "__main__":
    main()

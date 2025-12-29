#!/usr/bin/env python3
"""
One-time setup script for AgentCore Memory resources.

This script creates the AgentCore Memory resource with multiple strategies
(USER_PREFERENCE and SEMANTIC) for persistent customer context storage.

Run this once before deploying your agent:
    python scripts/setup_memory.py
"""

import os
import sys

from dotenv import load_dotenv

# 加載 .env 文件
load_dotenv()

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType


def setup_memory():
    """Create AgentCore Memory resource with customer support strategies."""
    region = os.getenv("AWS_REGION", "us-east-1")
    memory_client = MemoryClient(region_name=region)
    memory_name = "CustomerSupportMemory"

    print("=" * 70)
    print("AgentCore Memory Setup - Lab 2")
    print("=" * 70)
    print(f"Region: {region}")
    print()

    # Check if memory already exists from environment
    existing_memory_id = os.getenv("AGENTCORE_MEMORY_ID")
    if existing_memory_id:
        try:
            memory_client.gmcp_client.get_memory(memoryId=existing_memory_id)
            print(f"✅ Found existing memory resource: {existing_memory_id}")
            print()
            print("Memory resource is already configured!")
            print(f"Add this to your .env file if not already present:")
            print(f"    AGENTCORE_MEMORY_ID={existing_memory_id}")
            return existing_memory_id
        except Exception:
            print(f"⚠️  Memory ID in environment ({existing_memory_id}) not found.")
            print("Creating new memory resource...")
            print()

    # Create new memory resource with multiple strategies
    print("Creating AgentCore Memory resource...")
    print("This can take a couple of minutes...")
    print()

    strategies = [
        {
            StrategyType.USER_PREFERENCE.value: {
                "name": "CustomerPreferences",
                "description": "Captures customer preferences and behavior",
                "namespaces": ["support/customer/{actorId}/preferences"],
            }
        },
        {
            StrategyType.SEMANTIC.value: {
                "name": "CustomerSupportSemantic",
                "description": "Stores facts from conversations",
                "namespaces": ["support/customer/{actorId}/semantic"],
            }
        },
    ]

    try:
        response = memory_client.create_memory_and_wait(
            name=memory_name,
            description="Customer support agent memory",
            strategies=strategies,
            event_expiry_days=90,  # Memories expire after 90 days
        )

        memory_id = response["id"]

        print("✅ Memory resource created successfully!")
        print()
        print("=" * 70)
        print("IMPORTANT: Save this Memory ID")
        print("=" * 70)
        print()
        print(f"Memory ID: {memory_id}")
        print()
        print("Add this to your .env file:")
        print(f"    AGENTCORE_MEMORY_ID={memory_id}")
        print()
        print("Or export it in your shell:")
        print(f"    export AGENTCORE_MEMORY_ID={memory_id}")
        print()
        print("=" * 70)
        print()
        print("Memory Strategies Configured:")
        print("  • USER_PREFERENCE: Customer preferences and behavior")
        print("  • SEMANTIC: Factual information from conversations")
        print()
        print("Namespace pattern: support/customer/{{actorId}}/{{strategy}}")
        print("Event expiry: 90 days")
        print()

        return memory_id

    except Exception as e:
        print(f"❌ Memory creation failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check your AWS credentials are configured")
        print("  2. Verify you have permissions for Bedrock AgentCore")
        print("  3. Ensure AWS_REGION is set correctly")
        sys.exit(1)


if __name__ == "__main__":
    memory_id = setup_memory()

    # Optional: Seed sample customer history
    print("=" * 70)
    response = input("Would you like to seed sample customer history? (y/N): ")

    if response.lower() == "y":
        print()
        print("Seeding sample customer history...")

        region = os.getenv("AWS_REGION", "us-east-1")
        memory_client = MemoryClient(region_name=region)

        # Sample customer identifier
        CUSTOMER_ID = os.getenv("TEST_CUSTOMER_ID", "test_customer_001")

        # Previous customer interactions for seeding
        previous_interactions = [
            ("I bought a new iPhone 15 Pro. The Order number is 12345.", "USER"),
            (
                "Thank you for your purchase! I can see your iPhone 15 Pro order #12345 has been processed.",
                "ASSISTANT",
            ),
            (
                "What is the warranty period for the Sennheiser headphones on June 20th. Order number 654321.",
                "USER",
            ),
            (
                "Perfect! I have your Sennheiser headphones order #654321 on file with the 1-year warranty.",
                "ASSISTANT",
            ),
            ("I'm looking for a good laptop. I prefer ThinkPad models.", "USER"),
            (
                "Great choice! ThinkPads are excellent for their durability and performance. Let me help you find the right model for your needs.",
                "ASSISTANT",
            ),
        ]

        try:
            memory_client.create_event(
                memory_id=memory_id,
                actor_id=CUSTOMER_ID,
                session_id="previous_session",
                messages=previous_interactions,
            )
            print("✅ Seeded customer history successfully")
            print("   • iPhone 15 Pro order #12345")
            print("   • Sennheiser headphones order #654321")
            print("   • ThinkPad laptop preference")
            print()
            print(f"Sample customer ID: {CUSTOMER_ID}")
        except Exception as e:
            print(f"⚠️  Failed to seed history: {e}")

    print()
    print("=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Add AGENTCORE_MEMORY_ID to your .env file")
    print("  2. Run your agent: uv run test_agent_local.py")
    print("  3. Test memory by asking about customer preferences")
    print()

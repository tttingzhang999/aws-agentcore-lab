"""Technical support and web search tools."""

from strands import tool


@tool
def get_technical_support(query: str) -> str:
    """
    Get technical support information and troubleshooting steps.

    Args:
        query: Technical issue or question

    Returns:
        Troubleshooting steps and support information
    """
    support_kb = {
        "phone won't turn on": {
            "issue": "Device Not Powering On",
            "steps": [
                "1. Press and hold Power button for 10-15 seconds",
                "2. Connect to charger and wait 15 minutes",
                "3. Try different charging cable and adapter",
                "4. Check for physical damage to charging port",
                "5. If still not working, contact authorized service center",
            ],
            "warning": (
                "Do not attempt to open the device yourself as it may " "void warranty."
            ),
        },
        "wifi not connecting": {
            "issue": "WiFi Connection Problems",
            "steps": [
                "1. Toggle WiFi off and on in device settings",
                "2. Forget network and reconnect with password",
                "3. Restart your device",
                "4. Restart your WiFi router",
                "5. Check if other devices can connect to same network",
                "6. Reset network settings (Settings > General > Reset > "
                "Reset Network Settings)",
            ],
            "warning": (
                "Resetting network settings will remove all saved WiFi passwords."
            ),
        },
        "slow performance": {
            "issue": "Device Running Slowly",
            "steps": [
                "1. Close unused apps running in background",
                "2. Clear app cache (Settings > Storage > Clear Cache)",
                "3. Uninstall unused apps",
                "4. Check available storage space (need at least 10% free)",
                "5. Restart device",
                "6. Check for software updates",
                "7. Consider factory reset as last resort (backup data first)",
            ],
            "warning": "Always backup important data before performing factory reset.",
        },
    }

    query_lower = query.lower().strip()

    # Find matching support article
    for key, kb_item in support_kb.items():
        if any(word in query_lower for word in key.split()):
            steps_formatted = "\n".join(kb_item["steps"])
            return f"""
Technical Support: {kb_item['issue']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Troubleshooting Steps:
{steps_formatted}

⚠️ Important: {kb_item['warning']}

If these steps don't resolve the issue, please contact our technical support
team:
📞 Phone: 1-800-SUPPORT
💬 Live Chat: Available 24/7 on our website
📧 Email: support@example.com
"""

    # Generic support response
    return f"""
Technical Support Assistance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thank you for contacting technical support regarding: "{query}"

General Troubleshooting Steps:
1. Restart your device
2. Check for software updates
3. Verify all connections are secure
4. Consult product manual for specific guidance

For specialized assistance, please contact:
📞 Phone: 1-800-SUPPORT (Available 24/7)
💬 Live Chat: support.example.com
📧 Email: support@example.com

Our technical team will be happy to help resolve your issue!
"""

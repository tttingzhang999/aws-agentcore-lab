"""Technical support and web search tools."""

from strands import tool


@tool
def web_search(query: str) -> str:
    """
    Search the web for updated product information, reviews, and troubleshooting
    guides.

    Args:
        query: Search query for product information or support

    Returns:
        Simulated web search results (in production, would integrate with
        real search API)
    """
    # Simulated search results - in production, integrate with actual search API
    common_searches = {
        "samsung galaxy s22 screen replacement": {
            "title": "Official Samsung Screen Repair Service",
            "snippet": (
                "Screen replacement costs $199-$279 depending on damage. "
                "Includes 90-day warranty. Book appointment online or visit "
                "service center."
            ),
            "source": "samsung.com/support",
        },
        "iphone 14 battery life": {
            "title": "iPhone 14 Battery Performance Guide",
            "snippet": (
                "Expected battery life: Up to 20 hours video playback. "
                "Tips to extend battery: Enable Low Power Mode, reduce screen "
                "brightness, disable background app refresh."
            ),
            "source": "apple.com/support",
        },
        "macbook pro overheating": {
            "title": "MacBook Pro Temperature Management",
            "snippet": (
                "Common causes: Resource-intensive apps, blocked vents, "
                "outdated software. Solutions: Update macOS, reset SMC, "
                "use cooling pad, check Activity Monitor for CPU usage."
            ),
            "source": "apple.com/support",
        },
    }

    query_lower = query.lower().strip()

    # Try to find matching search result
    for key, result in common_searches.items():
        if any(word in query_lower for word in key.split()):
            return f"""
Web Search Results for: "{query}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 {result['title']}
{result['snippet']}

Source: {result['source']}

Note: For the most current information, please visit the official manufacturer
website.
"""

    # Generic response if no specific match
    return f"""
Web Search Results for: "{query}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I found general information about your query. For the most accurate and
up-to-date details:

• Visit official manufacturer websites
• Check recent product reviews on tech sites
• Consult user forums and community discussions

Would you like me to help you with something more specific?
"""

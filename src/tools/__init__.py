"""Customer support tools for the AgentCore agent.

Local tools (run within agent):
- get_product_info: Product information queries
- get_return_policy: Return policy information
- get_technical_support: Technical support guides
- add_numbers: Simple calculator (demo tool)

Gateway MCP tools (run in Lambda via AgentCore Gateway):
- check_warranty_status: Query warranty from DynamoDB
- web_search: Web search via DuckDuckGo
"""

from tools.add_numbers import add_numbers
from tools.get_product_info import get_product_info
from tools.get_return_policy import get_return_policy
from tools.get_technical_support import get_technical_support

__all__ = [
    "add_numbers",
    "get_product_info",
    "get_return_policy",
    "get_technical_support",
]

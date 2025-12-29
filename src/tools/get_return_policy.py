"""Product information and policy tools."""

from strands import tool


@tool
def get_return_policy(product_category: str) -> str:
    """
    Get return policy information for a specific product category.

    Args:
        product_category: Electronics category (e.g., 'smartphones', 'laptops',
            'accessories')

    Returns:
        Formatted return policy details including timeframes and conditions
    """
    policies = {
        "smartphones": {
            "return_window": "30 days",
            "condition": "Must be in original packaging with all accessories",
            "refund_method": "Original payment method or store credit",
            "restocking_fee": "No fee if unopened, 15% if opened",
        },
        "laptops": {
            "return_window": "30 days",
            "condition": "Must include all original accessories and packaging",
            "refund_method": "Original payment method",
            "restocking_fee": "No fee if defective, 20% if customer preference",
        },
        "accessories": {
            "return_window": "14 days",
            "condition": "Unused and in original packaging",
            "refund_method": "Original payment method or store credit",
            "restocking_fee": "No fee",
        },
    }

    category_lower = product_category.lower()
    policy = policies.get(category_lower)

    if not policy:
        return (
            f"Return policy for '{product_category}' category not found. "
            "Please contact customer support for details."
        )

    return f"""
Return Policy for {product_category.title()}:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Return Window: {policy['return_window']}
• Condition: {policy['condition']}
• Refund Method: {policy['refund_method']}
• Restocking Fee: {policy['restocking_fee']}

Note: All returns require original receipt or order number.
"""

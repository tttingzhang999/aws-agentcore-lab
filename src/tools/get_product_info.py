"""Product information and policy tools."""

from strands import tool


@tool
def get_product_info(product_name: str) -> str:
    """
    Get detailed information about a specific product.

    Args:
        product_name: Name of the product to look up

    Returns:
        Product details including price, specifications, and availability
    """
    products = {
        "samsung galaxy s22": {
            "name": "Samsung Galaxy S22",
            "price": "$799.99",
            "specs": (
                '6.1" AMOLED Display, Snapdragon 8 Gen 1, 50MP Camera, '
                "8GB RAM, 128GB Storage"
            ),
            "stock": "In Stock",
            "warranty": "1 year manufacturer warranty",
            "category": "smartphones",
        },
        "samsung galaxy s23": {
            "name": "Samsung Galaxy S23",
            "price": "$899.99",
            "specs": (
                '6.1" AMOLED Display, Snapdragon 8 Gen 2, 50MP Camera, '
                "8GB RAM, 256GB Storage"
            ),
            "stock": "In Stock",
            "warranty": "1 year manufacturer warranty",
            "category": "smartphones",
        },
        "iphone 14": {
            "name": "iPhone 14",
            "price": "$899.99",
            "specs": (
                '6.1" Super Retina XDR Display, A15 Bionic, 12MP Dual Camera, '
                "6GB RAM, 128GB Storage"
            ),
            "stock": "Limited Stock",
            "warranty": "1 year AppleCare",
            "category": "smartphones",
        },
        "macbook pro 14": {
            "name": 'MacBook Pro 14"',
            "price": "$1,999.99",
            "specs": '14" Liquid Retina XDR, M3 Pro Chip, 18GB RAM, 512GB SSD',
            "stock": "In Stock",
            "warranty": "1 year AppleCare",
            "category": "laptops",
        },
        "airpods pro": {
            "name": "AirPods Pro (2nd generation)",
            "price": "$249.99",
            "specs": (
                "Active Noise Cancellation, Transparency Mode, " "MagSafe Charging Case"
            ),
            "stock": "In Stock",
            "warranty": "1 year manufacturer warranty",
            "category": "accessories",
        },
    }

    product_key = product_name.lower().strip()
    product = products.get(product_key)

    if not product:
        return (
            f"Product '{product_name}' not found in our catalog. "
            "Please check the product name or contact support."
        )

    return f"""
Product Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{product['name']}

💰 Price: {product['price']}
📱 Specifications: {product['specs']}
📦 Availability: {product['stock']}
🛡️ Warranty: {product['warranty']}
🏷️ Category: {product['category'].title()}
"""

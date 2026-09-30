"""TechZone demo catalog — 12 products with prices, specs, stock.

Used by POST /api/tenants/{id}/seed-demo and by the standalone demo page mock.
"""
TECHZONE_PRODUCTS = [
    {"name": "Volt X1 Laptop", "price": 899, "currency": "USD",
     "specs": ["Intel Core i7 13th gen", "16GB RAM", "512GB SSD", '15.6" FHD display',
               "8hr battery"], "stock": 14, "url": "/products/volt-x1"},
    {"name": "Volt X1 Pro Laptop", "price": 1199, "currency": "USD",
     "specs": ["Intel Core i9 13th gen", "32GB RAM", "1TB SSD", '15.6" 2K display',
               "10hr battery", "RTX 4050"], "stock": 6, "url": "/products/volt-x1-pro"},
    {"name": "VoltTab 11 Tablet", "price": 349, "currency": "USD",
     "specs": ['11" 2K display', "8GB RAM", "128GB storage", "stylus included",
               "12hr battery"], "stock": 22, "url": "/products/volttab-11"},
    {"name": "Nova 27\" 4K Monitor", "price": 329, "currency": "USD",
     "specs": ['27" 4K UHD', "144Hz", "HDR400", "HDMI + DisplayPort"], "stock": 9,
     "url": "/products/nova-27-4k"},
    {"name": "Nova 24\" 1080p Monitor", "price": 149, "currency": "USD",
     "specs": ['24" Full HD', "100Hz", "HDMI + VGA"], "stock": 31,
     "url": "/products/nova-24"},
    {"name": "Pulse Buds Pro", "price": 79, "currency": "USD",
     "specs": ["Active noise cancellation", "Bluetooth 5.3", "36hr total battery",
               "wireless charging"], "stock": 48, "url": "/products/pulse-buds-pro"},
    {"name": "Pulse Buds Lite", "price": 39, "currency": "USD",
     "specs": ["Bluetooth 5.2", "24hr total battery", "touch controls"], "stock": 73,
     "url": "/products/pulse-buds-lite"},
    {"name": "BoomBox Mini Speaker", "price": 59, "currency": "USD",
     "specs": ["360° sound", "IPX7 waterproof", "18hr playtime", "Bluetooth 5.3"],
     "stock": 26, "url": "/products/boombox-mini"},
    {"name": "MechKey 75 Keyboard", "price": 89, "currency": "USD",
     "specs": ["75% layout", "hot-swappable switches", "RGB", "Bluetooth + 2.4GHz + USB-C"],
     "stock": 17, "url": "/products/mechkey-75"},
    {"name": "SwiftMouse Pro", "price": 59, "currency": "USD",
     "specs": ["26K DPI sensor", "90hr battery", "ergonomic", "2.4GHz + Bluetooth"],
     "stock": 40, "url": "/products/swiftmouse-pro"},
    {"name": "ChargeHub 65W GaN", "price": 45, "currency": "USD",
     "specs": ["65W GaN fast charging", "2x USB-C + 1x USB-A", "foldable plugs"],
     "stock": 55, "url": "/products/chargehub-65w"},
    {"name": "PowerBank 20000mAh", "price": 35, "currency": "USD",
     "specs": ["20000mAh", "22.5W fast charge", "USB-C + USB-A", "LED display"],
     "stock": 0, "url": "/products/powerbank-20k"},
]

TECHZONE_POLICIES = [
    {"type": "shipping",
     "text": "Free shipping on orders over $50 (otherwise $4.95 flat). Orders ship "
             "within 24 hours, delivery in 3-5 business days via TCS. Cash on delivery "
             "available nationwide."},
    {"type": "returns",
     "text": "14-day easy returns: unopened items get a full refund, opened items "
             "get store credit. Warranty claims are handled in-store within the "
             "1-year official warranty period."},
    {"type": "warranty",
     "text": "Every TechZone product carries a 1-year official warranty. Laptops "
             "and tablets include free first-year accidental-damage cover."},
]

TECHZONE_FAQS = [
    {"q": "Do you offer cash on delivery?",
     "a": "Yes — cash on delivery is available nationwide on all orders."},
    {"q": "How long does delivery take?",
     "a": "Orders ship within 24 hours and arrive in 3-5 business days."},
    {"q": "Can I return a product?",
     "a": "Yes, within 14 days. Unopened items get a full refund; opened items "
           "get store credit."},
]

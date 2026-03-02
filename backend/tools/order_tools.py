"""
Step 1–2: Domain model and tool implementations.

Concepts:
- Tools are plain Python functions. The LLM will call them by name with arguments.
- We load mock data from data/orders.json. In production you’d replace this with DB queries.
- Each function returns a string or dict that the LLM can use to phrase a natural-language reply.
- "Contract": tool name + docstring (description for the LLM) + typed parameters.
"""

import json
from pathlib import Path
from typing import Optional

# Path to mock data: same directory as this file -> parent -> data
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_ORDERS_PATH = _DATA_DIR / "orders.json"


def _load_orders() -> list[dict]:
    """Load orders from JSON. Cached in memory for the process lifetime."""
    with open(_ORDERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_order_status(customer_id: str, order_id: Optional[str] = None) -> str:
    """
    Get the status of an order for a customer.
    If order_id is not provided, returns the most recent order for this customer.
    Use when the user asks "where is my order", "order status", "what's the status of my order".
    """
    orders = _load_orders()
    if order_id:
        for o in orders:
            if o["order_id"] == order_id and o["customer_id"] == customer_id:
                return _format_order_status(o)
        return f"No order found with ID {order_id} for this customer."
    # Most recent = last in list (we could sort by placed_at)
    customer_orders = [o for o in orders if o["customer_id"] == customer_id]
    if not customer_orders:
        return "You don't have any orders yet."
    latest = customer_orders[-1]
    return _format_order_status(latest)


def _format_order_status(o: dict) -> str:
    status = o["status"].replace("_", " ").title()
    eta = o.get("eta_minutes", 0)
    items = ", ".join(f"{x['quantity']}x {x['name']}" for x in o["items"])
    return (
        f"Order {o['order_id']}: status is {status}. "
        f"Items: {items}. "
        + (f"ETA {eta} minutes." if eta else "Already delivered.")
    )


def get_tracking_info(customer_id: str, order_id: Optional[str] = None) -> str:
    """
    Get tracking details for an order (driver, current step, ETA).
    If order_id is omitted, use the customer's most recent order.
    Use when the user asks "track my order", "where's my delivery", "tracking".
    """
    orders = _load_orders()
    if order_id:
        for o in orders:
            if o["order_id"] == order_id and o["customer_id"] == customer_id:
                return _format_tracking(o)
        return f"No order found with ID {order_id} for this customer."
    customer_orders = [o for o in orders if o["customer_id"] == customer_id]
    if not customer_orders:
        return "You don't have any orders to track."
    return _format_tracking(customer_orders[-1])


def _format_tracking(o: dict) -> str:
    t = o.get("tracking")
    if not t:
        if o["status"] == "delivered":
            return f"Order {o['order_id']} was already delivered."
        return f"Order {o['order_id']} is {o['status']}. No live tracking yet; ETA about {o.get('eta_minutes', '?')} minutes."
    return (
        f"Order {o['order_id']}: {t.get('current_step', 'On the way')}. "
        f"Driver: {t.get('driver_name', 'N/A')}. "
        f"Estimated arrival: {t.get('estimated_arrival', 'soon')}."
    )


def reorder_last_order(customer_id: str) -> str:
    """
    Reorder the same items as the customer's most recent order.
    Use when the user says "reorder", "same order again", "order the same thing".
    """
    orders = _load_orders()
    customer_orders = [o for o in orders if o["customer_id"] == customer_id]
    if not customer_orders:
        return "You don't have a previous order to reorder."
    last = customer_orders[-1]
    items = ", ".join(f"{x['quantity']}x {x['name']}" for x in last["items"])
    # In a real system we'd create a new order; here we just confirm
    return (
        f"I've placed a reorder for: {items}. "
        f"Total ${last['total_usd']}. "
        "You'll get a confirmation and ETA shortly."
    )


def get_faq(question: str) -> str:
    """
    Answer common questions about refunds, cancellation, delivery times, contact.
    Use when the user asks about policy, refund, cancel, how to contact, delivery area, etc.
    """
    q = question.lower()
    if "refund" in q or "money back" in q:
        return "Refunds are available within 30 minutes of delivery for incorrect or missing items. Request via the app or call support."
    if "cancel" in q:
        return "You can cancel an order for free before the restaurant confirms. After that, a small fee may apply."
    if "contact" in q or "support" in q or "help" in q:
        return "Support: in-app chat 24/7, or call 1-800-QUICKBIT between 8am and 10pm."
    if "delivery" in q and ("time" in q or "long" in q or "how long" in q):
        return "Delivery usually takes 25–45 minutes depending on distance and restaurant readiness."
    return "I didn't find a specific answer for that. You can say 'contact support' for help, or ask about your order status or tracking."

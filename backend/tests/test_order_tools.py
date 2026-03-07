"""
Tests for order tools (get_order_status, get_tracking_info, reorder_last_order, get_faq, cancel_order).
Run from backend/: python -m pytest tests/ -v   or   python -m unittest discover -s tests -v
"""

import unittest
from tools.order_tools import get_order_status, get_tracking_info, reorder_last_order, get_faq, cancel_order


class TestOrderTools(unittest.TestCase):
    def test_get_order_status_returns_most_recent_for_customer(self):
        reply = get_order_status("cust-alice")
        self.assertIn("QB-", reply)
        self.assertIn("status", reply.lower())

    def test_get_order_status_unknown_customer(self):
        reply = get_order_status("cust-nonexistent")
        self.assertIn("don't have any orders", reply)

    def test_get_tracking_info_for_customer(self):
        reply = get_tracking_info("cust-alice")
        self.assertTrue(len(reply) > 0)
        self.assertIn("QB-", reply)

    def test_reorder_last_order(self):
        reply = reorder_last_order("cust-alice")
        self.assertIn("reorder", reply.lower())
        self.assertIn("$", reply)

    def test_get_faq_refund(self):
        reply = get_faq("What is your refund policy?")
        self.assertIn("refund", reply.lower())

    def test_cancel_order(self):
        reply = cancel_order("cust-alice")
        self.assertIn("cancelled", reply.lower())

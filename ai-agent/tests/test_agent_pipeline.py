"""
Automated unit and integration test suite for the Reasoner and Analytics layers.
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.reasoner import Reasoner
from agent.analyzer import Analyzer, parse_amount
from agent.executor import Executor


class TestBillerQAgentPipeline(unittest.TestCase):
    """Test suite verifying BillerQ AI Assistant's Reasoning + Analytics architecture."""

    def test_amount_parsing(self):
        """Test currency string conversions to float."""
        self.assertEqual(parse_amount("5,521.22"), 5521.22)
        self.assertEqual(parse_amount("1,000"), 1000.0)
        self.assertEqual(parse_amount(None), 0.0)
        self.assertEqual(parse_amount(250.5), 250.5)

    def test_reasoner_rule_plans(self):
        """Test rule-based templates for standard intents."""
        reasoner = Reasoner()
        
        # Test CUSTOMER_PROFILE intent
        plan_profile = asyncio.run(reasoner.generate_plan(
            intent="CUSTOMER_PROFILE",
            entities={"customer_name": "Joy P"}
        ))
        self.assertEqual(len(plan_profile["steps"]), 1)
        self.assertEqual(plan_profile["steps"][0]["tool"], "get_customer_profile")
        self.assertEqual(plan_profile["steps"][0]["arguments"], {"customer_id": "$customer_id"})

        # Test ANALYTICS intent
        plan_analytics = asyncio.run(reasoner.generate_plan(
            intent="ANALYTICS",
            entities={}
        ))
        tools = [step["tool"] for step in plan_analytics["steps"]]
        self.assertIn("get_dashboard_data", tools)
        self.assertIn("get_connection_data", tools)
        self.assertIn("get_customer_status_count", tools)

    def test_kpi_calculation(self):
        """Test KPI calculation parses values into correct structure."""
        analyzer = Analyzer()
        
        mock_raw_data = {
            "dashboard": {
                "payment_collection": {
                    "today": "150.00",
                    "this_month": "12,450.50",
                    "dues": "95,000.00",
                    "wallet_amount": "5,000.00"
                },
                "subscriptions": {
                    "expired": 5,
                    "in_five_days": 10
                },
                "complaints": {
                    "total": 12,
                    "un_resolved": 8,
                    "in_process": 2,
                    "resolved": 2
                }
            },
            "connections": {
                "collection_chart": {
                    "data": ["0", "500", "1200"]
                }
            },
            "customer_status": [
                {"status": "Active", "count": 100},
                {"status": "Inactive", "count": 10},
                {"status": "Total", "count": 110}
            ],
            "complaints_status": [
                {"status": "Open", "count": 8},
                {"status": "In Progress", "count": 2},
                {"status": "Closed", "count": 2}
            ],
            "package_report": {
                "packages": {
                    "data": [
                        {"package_name": "TP Pack", "invoice_count": 50, "grand_total": "25,000.00"},
                        {"package_name": "Base Pack", "invoice_count": 80, "grand_total": "16,000.00"}
                    ]
                }
            }
        }

        kpis = analyzer.compute_kpis(mock_raw_data)
        
        # Verify collection metrics
        self.assertEqual(kpis["collection"]["today"], 150.0)
        self.assertEqual(kpis["collection"]["this_month"], 12450.5)
        self.assertEqual(kpis["collection"]["dues"], 95000.0)
        self.assertEqual(kpis["collection"]["wallet_amount"], 5000.0)
        
        # Verify customer metrics
        self.assertEqual(kpis["customer"]["total"], 110)
        self.assertEqual(kpis["customer"]["active"], 100)
        self.assertEqual(kpis["customer"]["inactive"], 10)
        
        # Verify complaints metrics
        self.assertEqual(kpis["complaints"]["total"], 12)
        self.assertEqual(kpis["complaints"]["open"], 8)
        self.assertEqual(kpis["complaints"]["in_progress"], 2)
        
        # Verify subscription and package popularity
        self.assertEqual(kpis["subscription"]["expired"], 5)
        self.assertEqual(kpis["subscription"]["expiring_soon"], 10)
        self.assertEqual(len(kpis["subscription"]["popular_packages"]), 2)
        
        # Base Pack has 80 subscribers so it should be first
        self.assertEqual(kpis["subscription"]["popular_packages"][0]["package_name"], "Base Pack")
        self.assertEqual(kpis["subscription"]["popular_packages"][1]["package_name"], "TP Pack")

    def test_list_truncation_to_10(self):
        """Test that lists with > 10 items are truncated to 10 with a count suffix."""
        from agent.formatter import sanitize_and_truncate_data
        
        # List of 15 elements
        test_list = [f"item_{i}" for i in range(15)]
        truncated = sanitize_and_truncate_data(test_list, max_list_len=10)
        
        self.assertEqual(len(truncated), 11)
        self.assertEqual(truncated[-1], "... (5 more items truncated)")
        self.assertEqual(truncated[0], "item_0")
        self.assertEqual(truncated[9], "item_9")


if __name__ == "__main__":
    unittest.main()

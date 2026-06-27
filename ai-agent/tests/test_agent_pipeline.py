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

    def test_executor_substitution(self):
        """Test step execution substitutes place-holders correctly."""
        executor = Executor()
        
        # Mock global tools call map
        from agent import executor as exec_module
        original_map = exec_module.TOOL_MAP
        
        mock_tool_func = AsyncMock(return_value={"id": 44350, "name": "Joy P"})
        exec_module.TOOL_MAP = {
            "get_customer_profile": mock_tool_func
        }

        plan = {
            "steps": [
                {
                    "tool": "get_customer_profile",
                    "arguments": {"customer_id": "$customer_id"}
                }
            ]
        }
        resolved_entities = {
            "$customer_id": 44350
        }

        try:
            results = asyncio.run(executor.execute_steps(plan, resolved_entities))
            
            # Check execution args passed to lambda mock
            mock_tool_func.assert_called_once_with({"customer_id": 44350})
            self.assertEqual(results["get_customer_profile"]["name"], "Joy P")
        finally:
            # Restore TOOL_MAP
            exec_module.TOOL_MAP = original_map

    def test_specific_metric_query_handling(self):
        """Test that specific queries are detected correctly."""
        from agent.formatter import _is_specific_metric_query
        
        # Specific queries
        self.assertTrue(_is_specific_metric_query("today's payment collection"))
        self.assertTrue(_is_specific_metric_query("how many active customers?"))
        self.assertTrue(_is_specific_metric_query("show the count of suspended customers"))
        
        # General queries
        self.assertFalse(_is_specific_metric_query("give me a business summary report"))
        self.assertFalse(_is_specific_metric_query("explain overall performance and insights"))
        self.assertFalse(_is_specific_metric_query("what are the key concerns and recommendations?"))

    def test_list_truncation_to_10(self):
        """Test that lists with > 10 items are truncated to 10 with a count suffix."""
        from agent.formatter import sanitize_and_truncate_data
        
        # List of 15 elements
        test_list = [f"item_{i}" for i in range(15)]
        truncated = sanitize_and_truncate_data(test_list, max_list_len=10)
        
        self.assertEqual(len(truncated), 11)
        self.assertEqual(truncated[-1], "+ 5 more")
        self.assertEqual(truncated[0], "item_0")
        self.assertEqual(truncated[9], "item_9")

    def test_redirection_links_appending(self):
        """Test that redirection links are correctly appended based on intent."""
        from agent.formatter import append_redirection_link
        
        # If link already exists, should not append
        response_with_link = "Check this out [customers](/customers)"
        self.assertEqual(append_redirection_link(response_with_link, "CUSTOMER_SEARCH"), response_with_link)
        
        # Append appropriate link
        self.assertIn("(/customers)", append_redirection_link("Here are your customers:", "CUSTOMER_SEARCH"))
        self.assertIn("(/billing/recurring)", append_redirection_link("Pending collection:", "UNPAID_CUSTOMERS"))
        self.assertIn("?id=123", append_redirection_link("Profile details:", "CUSTOMER_PROFILE", customer_id="123"))


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for the database-driven agent tools, SQL validation, and safety mechanisms.
"""
import unittest
from tools_db import validate_sql_query, execute_tool

class TestDatabaseAgentTools(unittest.TestCase):
    """Test suite verifying SQL validation and safety constraints."""

    def test_sql_validation_only_select(self):
        """Verify that insert, update, delete, drop statements are rejected."""
        # Non-SELECT statements should be rejected
        with self.assertRaises(ValueError) as ctx:
            validate_sql_query("INSERT INTO customers (name) VALUES ('Hacker')", company_id=12)
        self.assertIn("not allowed", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            validate_sql_query("UPDATE customers SET status = 'active'", company_id=12)
        self.assertIn("not allowed", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            validate_sql_query("DELETE FROM customers WHERE id = 1", company_id=12)
        self.assertIn("not allowed", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            validate_sql_query("DROP TABLE customers", company_id=12)
        self.assertIn("not allowed", str(ctx.exception).lower())

    def test_sql_validation_company_id_required(self):
        """Verify that company_id is strictly required for tables containing multi-tenant data."""
        # Query references 'customers' but doesn't filter by company_id
        with self.assertRaises(ValueError) as ctx:
            validate_sql_query("SELECT * FROM customers", company_id=12)
        self.assertIn("security validation failed", str(ctx.exception).lower())
        self.assertIn("missing the filter 'company_id = 12'", str(ctx.exception).lower())

        # Query references 'orders' but filters by wrong company_id
        with self.assertRaises(ValueError) as ctx:
            validate_sql_query("SELECT * FROM orders WHERE company_id = 99", company_id=12)
        self.assertIn("security validation failed", str(ctx.exception).lower())

    def test_sql_validation_company_id_success(self):
        """Verify that query passes validation when company_id filter is present."""
        # Standard query with matching company_id filter
        valid_query_1 = "SELECT * FROM customers WHERE company_id = 12"
        self.assertEqual(validate_sql_query(valid_query_1, company_id=12), valid_query_1)

        # Parameterized query with named parameter
        valid_query_2 = "SELECT * FROM customers WHERE company_id = :company_id"
        self.assertEqual(validate_sql_query(valid_query_2, company_id=12), valid_query_2)

    def test_execute_tool_schema(self):
        """Verify get_schema tool returns correct table list and table columns."""
        # Get all tables
        res_all = execute_tool("get_schema", {}, company_id=12)
        self.assertIn("tables", res_all)
        self.assertIn("customers", res_all["tables"])
        self.assertIn("orders", res_all["tables"])

        # Get specific table columns
        res_table = execute_tool("get_schema", {"table_name": "accounts"}, company_id=12)
        self.assertIn("accounts", res_table)
        self.assertIn("id:bigint", res_table["accounts"])
        self.assertIn("company_id:bigint", res_table["accounts"])

        # Invalid table name
        res_invalid = execute_tool("get_schema", {"table_name": "non_existent_table"}, company_id=12)
        self.assertIn("error", res_invalid)

if __name__ == "__main__":
    unittest.main()

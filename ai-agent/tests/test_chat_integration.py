"""
Integration tests for the /chat route, verifying the agent selection and fallback routing.
"""
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import app
from agent.memory import memory_manager

class TestChatRouting(unittest.TestCase):
    """Integration test suite verifying routing between REST and DB agents."""

    def setUp(self):
        self.client = TestClient(app)
        # Clear active sessions before each test
        memory_manager._sessions.clear()

    @patch("agent.agent_loop.BillerQAgent.run")
    def test_routing_to_rest_agent(self, mock_rest_run):
        """Verify that a standard query routes to the REST agent."""
        mock_rest_run.return_value = ("REST Agent Response", {"customer_id": 123})
        
        response = self.client.post(
            "/chat",
            json={
                "message": "details of Joy P",
                "session_id": "test-session-rest",
                "billerq_token": "mock-token"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["response"], "REST Agent Response")
        self.assertEqual(data["metadata"]["agent_type"], "rest_agent")
        
        # Verify REST agent was called and DB agent was not
        mock_rest_run.assert_called_once()

    @patch("agent.db_agent.run_agent")
    @patch("agent.agent_loop.BillerQAgent.run")
    def test_routing_to_db_agent(self, mock_rest_run, mock_db_run):
        """Verify that a query with DB/SQL keywords routes to the DB agent."""
        mock_db_run.return_value = ("DB SQL Response", [{"role": "user", "content": "..."}])
        
        response = self.client.post(
            "/chat",
            json={
                "message": "run a query: SELECT id FROM accounts WHERE company_id = 1",
                "session_id": "test-session-db",
                "billerq_token": "mock-token"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["response"], "DB SQL Response")
        self.assertEqual(data["metadata"]["agent_type"], "db_agent")
        
        # Verify DB agent was called and REST agent was not
        mock_db_run.assert_called_once()
        mock_rest_run.assert_not_called()

    @patch("agent.db_agent.run_agent")
    @patch("agent.agent_loop.BillerQAgent.run")
    def test_db_agent_fallback_to_rest(self, mock_rest_run, mock_db_run):
        """Verify that if the DB agent fails (e.g. timeout), it falls back to the REST agent."""
        # DB agent raises connection timeout
        mock_db_run.side_effect = ConnectionError("Can't connect to MySQL server")
        # REST agent completes successfully
        mock_rest_run.return_value = ("REST Fallback Response", {"customer_id": 456})
        
        response = self.client.post(
            "/chat",
            json={
                "message": "show me the database schema",
                "session_id": "test-session-fallback",
                "billerq_token": "mock-token"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["response"], "REST Fallback Response")
        self.assertEqual(data["metadata"]["agent_type"], "rest_agent")
        
        # Verify both were called (DB first, then REST as fallback)
        mock_db_run.assert_called_once()
        mock_rest_run.assert_called_once()

if __name__ == "__main__":
    unittest.main()

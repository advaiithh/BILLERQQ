import os
import json
import logging
from agent.tool_registry import select_modules, get_selected_tools
from agent.cache import billerq_cache
from agent.reducer import compact_api_result

def test_tool_registry_module_selection():
    # Test complaints module selection
    modules_complaints = select_modules("I want to see billing complaints")
    assert "complaints" in modules_complaints
    assert "payments" in modules_complaints

    # Test flat tool lookup
    tools = get_selected_tools("show complaints")
    tool_names = [t["name"] for t in tools]
    assert "get_complaints" in tool_names
    assert "get_complaint_status_count" in tool_names
    # Should not include unrelated tools like get_enquiries
    assert "get_enquiries" not in tool_names

def test_caching_layer():
    company_id = "test_co"
    billerq_cache.set(company_id, "intent", "show open complaints", {"tool": "get_complaints"}, ttl_seconds=10)
    
    val = billerq_cache.get(company_id, "intent", "show open complaints")
    assert val is not None
    assert val["tool"] == "get_complaints"

    # Verify case and space insensitivity
    val_fuzzy = billerq_cache.get(company_id, "intent", "  SHOW OPEN COMPLAINTS  ")
    assert val_fuzzy is not None
    assert val_fuzzy["tool"] == "get_complaints"

def test_reducer_truncation():
    raw_data = {
        "total": 100,
        "data": [
            {"id": i, "name": f"Cust {i}", "subscriber_id": f"SUB{i}", "status": "Active", "unrelated_field": "x"*1000}
            for i in range(20)
        ]
    }
    
    reduced = compact_api_result("get_all_customers", raw_data)
    assert reduced["total"] == 100
    assert len(reduced["items"]) == 5
    # Check that unrelated_field is stripped
    assert "unrelated_field" not in reduced["items"][0]
    assert reduced["items"][0]["name"] == "Cust 0"

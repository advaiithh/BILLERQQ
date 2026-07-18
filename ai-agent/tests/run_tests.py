import sys
import os

# Add parent and tests dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from test_hybrid_optimizations import *

try:

    print("Running test_tool_registry_module_selection...")
    test_tool_registry_module_selection()
    print("test_tool_registry_module_selection passed!")

    print("Running test_caching_layer...")
    test_caching_layer()
    print("test_caching_layer passed!")

    print("Running test_reducer_truncation...")
    test_reducer_truncation()
    print("test_reducer_truncation passed!")
    
    print("\n[SUCCESS] All verification tests passed successfully!")
except AssertionError as e:
    print("\n[FAILURE] Verification failed with AssertionError!")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print("\n[FAILURE] Verification failed with exception!")
    import traceback
    traceback.print_exc()
    sys.exit(1)

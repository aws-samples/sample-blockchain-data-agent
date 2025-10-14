#!/usr/bin/env python3
"""
Test script to verify tool access is working correctly.
"""

def test_tool_name_access():
    """Test that we can access tool names correctly."""
    
    # Mock MCPAgentTool class to simulate the real object
    class MockMCPAgentTool:
        def __init__(self, name):
            self.name = name
        
        def __str__(self):
            return f"MockTool({self.name})"
    
    # Create mock tools
    tools = [
        MockMCPAgentTool("list_s3_buckets"),
        MockMCPAgentTool("get_glue_job_status"),
        MockMCPAgentTool("analyze_costs")
    ]
    
    print("🧪 Testing tool name access...")
    
    # Test the correct way (should work)
    try:
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            else:
                tool_names.append(str(tool))
        
        print(f"✅ Correct method works: {tool_names}")
    except Exception as e:
        print(f"❌ Correct method failed: {e}")
    
    # Test the incorrect way (should fail)
    try:
        incorrect_names = [tool['name'] for tool in tools]
        print(f"❌ Incorrect method should have failed but didn't: {incorrect_names}")
    except TypeError as e:
        print(f"✅ Incorrect method correctly failed with TypeError: {e}")
    except Exception as e:
        print(f"⚠️  Incorrect method failed with unexpected error: {e}")

if __name__ == "__main__":
    test_tool_name_access()
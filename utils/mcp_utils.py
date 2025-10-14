#!/usr/bin/env python3
"""
Utility functions for working with MCP tools and Strands Agents.
"""

from typing import List, Any


def get_tool_names(tools: List[Any]) -> List[str]:
    """
    Extract tool names from MCPAgentTool objects.
    
    This function handles the correct way to access tool names from
    MCPAgentTool objects, which are not subscriptable like dictionaries.
    
    Args:
        tools: List of MCPAgentTool objects
        
    Returns:
        List of tool names as strings
    """
    tool_names = []
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_names.append(tool.name)
        elif hasattr(tool, '__dict__') and 'name' in tool.__dict__:
            tool_names.append(tool.__dict__['name'])
        else:
            # Fallback to string representation
            tool_names.append(str(tool))
    
    return tool_names


def print_tools_info(tools: List[Any], server_name: str = "MCP Server") -> None:
    """
    Print information about loaded MCP tools.
    
    Args:
        tools: List of MCPAgentTool objects
        server_name: Name of the MCP server for display
    """
    if not tools:
        print(f"⚠️  No tools loaded from {server_name}")
        return
    
    tool_names = get_tool_names(tools)
    print(f"✅ Loaded {len(tools)} tools from {server_name}: {', '.join(tool_names)}")


def safe_tool_access_example():
    """
    Example of how to safely access tool information.
    """
    print("Example of safe tool access:")
    print("""
    # ✅ Correct way:
    tool_names = []
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_names.append(tool.name)
        else:
            tool_names.append(str(tool))
    
    # ❌ Incorrect way (will cause TypeError):
    tool_names = [tool['name'] for tool in tools]  # MCPAgentTool is not subscriptable
    """)


if __name__ == "__main__":
    # Run example
    safe_tool_access_example()
    
    # Test with mock tools
    class MockTool:
        def __init__(self, name):
            self.name = name
    
    mock_tools = [MockTool("tool1"), MockTool("tool2")]
    print_tools_info(mock_tools, "Test Server")
    
    names = get_tool_names(mock_tools)
    print(f"Extracted names: {names}")
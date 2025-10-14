#!/usr/bin/env python3
"""
Direct streaming test for blockchain_agent_agentcore.py

This script tests the streaming functionality by directly calling
the invoke_streaming function to see real-time event streaming.
"""

import asyncio
import json
import time
from blockchain_agent_agentcore import invoke_streaming


async def test_streaming_response():
    """Test the streaming response with a blockchain query."""
    print("🔄 Testing Direct Streaming Response")
    print("=" * 45)
    
    # Test payload - use a query that will take some time
    test_payload = {
        "prompt": "How many Bitcoin blocks were created in the last 7 days? Show me the daily breakdown."
    }
    
    print(f"📋 Query: {test_payload['prompt']}")
    print("\n🌊 Streaming Events:")
    print("-" * 50)
    
    event_count = 0
    start_time = time.time()
    
    try:
        async for event in invoke_streaming(test_payload):
            event_count += 1
            current_time = time.time() - start_time
            
            print(f"[{current_time:.2f}s] Event {event_count}:")
            
            if isinstance(event, dict):
                # Handle different event types
                if "error" in event:
                    print(f"  ❌ ERROR: {event['error']}")
                    break
                elif "data" in event:
                    # Text streaming data
                    data = event["data"]
                    print(f"  📟 DATA: {data}")
                elif "complete" in event:
                    print(f"  ✅ COMPLETE: {event.get('complete', False)}")
                elif "current_tool_use" in event:
                    tool_info = event["current_tool_use"]
                    if tool_info and "name" in tool_info:
                        print(f"  🔧 TOOL: {tool_info['name']}")
                elif "result" in event:
                    print(f"  🎯 RESULT: Event completed")
                else:
                    # Show other event types
                    event_keys = list(event.keys())[:3]  # First 3 keys
                    print(f"  📋 EVENT: {event_keys}")
            else:
                print(f"  📦 RAW: {type(event)} - {str(event)[:100]}...")
            
            print()  # Add spacing between events
    
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False
    
    end_time = time.time() - start_time
    print(f"✅ Streaming test completed!")
    print(f"📊 Total events: {event_count}")
    print(f"⏱️  Total time: {end_time:.2f} seconds")
    
    return event_count > 0


async def test_multiple_streaming_queries():
    """Test multiple streaming queries to see different patterns."""
    print("\n🔄 Testing Multiple Streaming Queries")
    print("=" * 45)
    
    test_queries = [
        "What databases are available?",  # Quick schema query
        "SELECT COUNT(*) FROM btc.blocks WHERE cast(date as date) = current_date LIMIT 1",  # Simple query
        "Show me the top 5 Ethereum transactions by gas price today"  # Complex query
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📋 Test {i}: {query}")
        print("-" * 30)
        
        payload = {"prompt": query}
        event_count = 0
        
        try:
            async for event in invoke_streaming(payload):
                event_count += 1
                
                # Show only key events for brevity
                if isinstance(event, dict):
                    if "error" in event:
                        print(f"  ❌ {event['error']}")
                        break
                    elif "data" in event:
                        # Show first 50 chars of data
                        data = event["data"][:50]
                        print(f"  📟 {data}{'...' if len(event['data']) > 50 else ''}")
                    elif "current_tool_use" in event and event["current_tool_use"]:
                        tool_name = event["current_tool_use"].get("name", "unknown")
                        print(f"  🔧 Using tool: {tool_name}")
            
            print(f"  ✅ Query {i} completed ({event_count} events)")
            
        except Exception as e:
            print(f"  ❌ Query {i} failed: {e}")


async def main():
    """Run all streaming tests."""
    print("🧪 Blockchain Agent Streaming Tests")
    print("=" * 40)
    
    print("💡 This script tests the streaming functionality by directly")
    print("   calling the invoke_streaming function from your agent.\n")
    
    # Test 1: Detailed streaming response
    success = await test_streaming_response()
    
    if success:
        # Test 2: Multiple queries
        await test_multiple_streaming_queries()
        
        print("\n🎉 All streaming tests completed!")
        print("\n📋 What you should see:")
        print("   • Real-time events as they occur")
        print("   • Tool execution events (🔧)")
        print("   • Data streaming events (📟)")
        print("   • Completion events (✅)")
        
    else:
        print("\n❌ Streaming test failed. Check your agent setup:")
        print("   • Ensure AWS credentials are configured")
        print("   • Verify MCP server is accessible")
        print("   • Check that dependencies are installed")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Interactive streaming test for blockchain agent

This script provides an interactive way to test streaming responses
with real-time display of events as they occur.
"""

import asyncio
import json
import time
from blockchain_agent_agentcore import invoke_streaming


class StreamingTester:
    """Interactive streaming test interface."""
    
    def __init__(self):
        self.event_count = 0
        self.start_time = None
    
    async def stream_with_display(self, query: str):
        """Stream a query with real-time display."""
        print(f"\n🔄 Streaming Query: {query}")
        print("=" * 60)
        
        payload = {"prompt": query}
        self.event_count = 0
        self.start_time = time.time()
        
        print("🌊 Live Streaming Events:")
        print("-" * 40)
        
        try:
            async for event in invoke_streaming(payload):
                await self._display_event(event)
                
                # Small delay to make streaming visible
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"\n❌ Streaming failed: {e}")
    
    async def _display_event(self, event):
        """Display a single streaming event with formatting."""
        self.event_count += 1
        elapsed = time.time() - self.start_time
        
        # Event header
        print(f"\n[{elapsed:6.2f}s] Event #{self.event_count}")
        
        if isinstance(event, dict):
            if "error" in event:
                print(f"❌ ERROR: {event['error']}")
                
            elif "data" in event:
                # Text streaming - this is the main content
                data = event["data"]
                print(f"📝 TEXT: {data}", end="", flush=True)
                
            elif "current_tool_use" in event:
                tool_info = event["current_tool_use"]
                if tool_info and isinstance(tool_info, dict):
                    tool_name = tool_info.get("name", "unknown")
                    tool_input = tool_info.get("input", {})
                    print(f"🔧 TOOL: {tool_name}")
                    if tool_input:
                        print(f"   Input: {json.dumps(tool_input, indent=2)[:100]}...")
                        
            elif "complete" in event:
                complete_status = event.get("complete", False)
                print(f"✅ COMPLETE: {complete_status}")
                
            elif "init_event_loop" in event:
                print("🔄 INIT: Event loop starting")
                
            elif "start_event_loop" in event:
                print("▶️  START: Processing cycle beginning")
                
            elif "message" in event:
                message = event["message"]
                role = message.get("role", "unknown")
                print(f"💬 MESSAGE: {role} message created")
                
            elif "result" in event:
                print("🎯 RESULT: Final result available")
                
            else:
                # Show unknown event types
                event_keys = [k for k in event.keys() if not k.startswith("_")][:3]
                print(f"📋 OTHER: {event_keys}")
        else:
            print(f"📦 RAW: {type(event)} - {str(event)[:50]}...")
    
    async def interactive_mode(self):
        """Run interactive streaming test mode."""
        print("🧪 Interactive Blockchain Agent Streaming Test")
        print("=" * 50)
        print("💡 Enter blockchain queries to see real-time streaming")
        print("   Type 'quit' to exit, 'examples' for sample queries\n")
        
        while True:
            try:
                query = input("🔍 Enter query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                    
                elif query.lower() == 'examples':
                    self._show_examples()
                    continue
                    
                elif not query:
                    continue
                
                # Stream the query
                await self.stream_with_display(query)
                
                # Summary
                elapsed = time.time() - self.start_time
                print(f"\n📊 Summary: {self.event_count} events in {elapsed:.2f}s")
                print("-" * 50)
                
            except KeyboardInterrupt:
                print("\n👋 Interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_examples(self):
        """Show example queries."""
        print("\n📋 Example Blockchain Queries:")
        print("   • How many Bitcoin blocks were created today?")
        print("   • Show me the top 5 Ethereum transactions by gas price")
        print("   • What are the most active TON DEX pools?")
        print("   • List all available databases")
        print("   • SELECT COUNT(*) FROM btc.blocks LIMIT 1")
        print("   • Analyze Ethereum gas prices for the last week")


async def quick_streaming_demo():
    """Run a quick streaming demonstration."""
    print("🚀 Quick Streaming Demo")
    print("=" * 25)
    
    tester = StreamingTester()
    
    demo_queries = [
        "What databases are available?",
        "How many Bitcoin blocks were created today?",
    ]
    
    for query in demo_queries:
        await tester.stream_with_display(query)
        print("\n" + "="*60)
        
        # Pause between queries
        await asyncio.sleep(2)


async def main():
    """Main test runner."""
    print("🧪 Blockchain Agent Streaming Tests")
    print("=" * 40)
    
    mode = input("Choose mode:\n  1. Quick Demo\n  2. Interactive Mode\n  Enter choice (1 or 2): ").strip()
    
    if mode == "1":
        await quick_streaming_demo()
    elif mode == "2":
        tester = StreamingTester()
        await tester.interactive_mode()
    else:
        print("Invalid choice. Running quick demo...")
        await quick_streaming_demo()


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
AgentCore streaming test using boto3 client

This script tests streaming by calling the deployed AgentCore agent
using the AWS SDK with streaming enabled.
"""

import boto3
import json
import time
import asyncio


def test_agentcore_streaming_sync():
    """Test AgentCore streaming using synchronous boto3 client."""
    print("🔄 Testing AgentCore Streaming (Sync)")
    print("=" * 40)
    
    try:
        # Initialize AgentCore client
        client = boto3.client('bedrock-agentcore', region_name='us-east-1')
        
        # Test payload
        payload = json.dumps({
            "prompt": "How many Bitcoin blocks were created today? Explain the process step by step."
        })
        
        print("📋 Query: Bitcoin blocks analysis")
        print("🌊 Streaming response:")
        print("-" * 30)
        
        # Make streaming request
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:YOUR_ACCOUNT:runtime/blockchain-agent',
            runtimeSessionId=f'test-session-{int(time.time())}',
            payload=payload
        )
        
        # Read streaming response
        event_count = 0
        for event in response['response']:
            event_count += 1
            
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    # Decode the chunk
                    chunk_data = json.loads(chunk['bytes'].decode('utf-8'))
                    print(f"Event {event_count}: {chunk_data}")
            
        print(f"\n✅ Received {event_count} streaming events")
        return True
        
    except Exception as e:
        print(f"❌ AgentCore streaming test failed: {e}")
        print("\n💡 Make sure:")
        print("   • Agent is deployed to AgentCore")
        print("   • Update the agentRuntimeArn with your actual ARN")
        print("   • AWS credentials have AgentCore permissions")
        return False


def test_agentcore_invoke_command():
    """Test using agentcore CLI command with different options."""
    print("\n🔄 Testing AgentCore CLI Commands")
    print("=" * 35)
    
    import subprocess
    
    test_commands = [
        {
            "name": "Simple Query",
            "cmd": ["agentcore", "invoke", "--agent", "blockchain-agent", 
                   '{"prompt": "What time is it?"}'],
            "description": "Basic query to test connectivity"
        },
        {
            "name": "Blockchain Query", 
            "cmd": ["agentcore", "invoke", "--agent", "blockchain-agent",
                   '{"prompt": "How many Bitcoin blocks today?"}'],
            "description": "Blockchain-specific query"
        },
        {
            "name": "Complex Analysis",
            "cmd": ["agentcore", "invoke", "--agent", "blockchain-agent",
                   '{"prompt": "Analyze Ethereum gas prices for the last 24 hours"}'],
            "description": "Complex query that should trigger streaming"
        }
    ]
    
    for test in test_commands:
        print(f"\n📋 {test['name']}: {test['description']}")
        print(f"Command: {' '.join(test['cmd'])}")
        
        try:
            result = subprocess.run(
                test['cmd'], 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ Success!")
                # Show first 200 chars of response
                response = result.stdout[:200]
                print(f"Response: {response}{'...' if len(result.stdout) > 200 else ''}")
            else:
                print("❌ Failed!")
                print(f"Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("⏱️  Timeout (60s) - query may be too complex")
        except Exception as e:
            print(f"❌ Command failed: {e}")


def main():
    """Run AgentCore streaming tests."""
    print("🧪 AgentCore Streaming Tests")
    print("=" * 30)
    
    print("💡 These tests verify streaming works with deployed AgentCore agent\n")
    
    # Test 1: Direct boto3 streaming (advanced)
    print("🔬 Test 1: Direct Streaming API")
    streaming_success = test_agentcore_streaming_sync()
    
    # Test 2: CLI commands (easier to use)
    print("\n🔬 Test 2: CLI Commands")
    test_agentcore_invoke_command()
    
    print("\n📋 Streaming Indicators to Look For:")
    print("   • Multiple response chunks/events")
    print("   • Progressive text generation")
    print("   • Tool execution notifications")
    print("   • Real-time query progress")
    
    print("\n💡 If streaming isn't working:")
    print("   • Check if agent is deployed: agentcore list")
    print("   • Verify agent name matches deployment")
    print("   • Ensure AWS credentials are configured")


if __name__ == "__main__":
    main()
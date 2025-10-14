#!/bin/bash
# AgentCore CLI Streaming Tests
# This script tests different ways to invoke the agent and observe streaming behavior

echo "🧪 AgentCore CLI Streaming Tests"
echo "================================"

# Check if agent is deployed
echo "🔍 Checking deployed agents..."
agentcore list

echo ""
echo "📋 Testing Different Query Types for Streaming Behavior"
echo "======================================================"

# Test 1: Simple query (may use sync mode)
echo ""
echo "📋 Test 1: Simple Query (likely sync mode)"
echo "Query: What time is it?"
echo "Expected: Quick single response"
echo ""
time agentcore invoke --agent blockchain-agent '{"prompt": "What time is it?"}'

# Test 2: Schema discovery (moderate complexity)
echo ""
echo "📋 Test 2: Schema Discovery (may trigger streaming)"
echo "Query: List all available databases"
echo "Expected: Progressive response as schemas are discovered"
echo ""
time agentcore invoke --agent blockchain-agent '{"prompt": "List all available databases in the data catalog"}'

# Test 3: Complex blockchain query (should trigger streaming)
echo ""
echo "📋 Test 3: Complex Blockchain Query (should stream)"
echo "Query: Bitcoin blocks analysis with explanation"
echo "Expected: Multiple events showing query generation, execution, results"
echo ""
time agentcore invoke --agent blockchain-agent '{"prompt": "How many Bitcoin blocks were created today? Explain the process you used to find this information."}'

# Test 4: Multi-step analysis (definitely should stream)
echo ""
echo "📋 Test 4: Multi-Step Analysis (should definitely stream)"
echo "Query: Comprehensive Ethereum analysis"
echo "Expected: Multiple tool calls, progressive analysis"
echo ""
time agentcore invoke --agent blockchain-agent '{"prompt": "Analyze Ethereum network activity for today: show me block count, transaction count, and average gas price. Explain each step."}'

echo ""
echo "🎯 Streaming Indicators to Look For:"
echo "=================================="
echo "✅ Progressive text generation (not all at once)"
echo "✅ Tool execution messages appearing in real-time"
echo "✅ Step-by-step explanations as they're generated"
echo "✅ Query execution progress updates"
echo ""
echo "❌ Non-Streaming Indicators:"
echo "✅ Complete response appears all at once"
echo "✅ No intermediate progress messages"
echo "✅ Single final result block"

echo ""
echo "💡 To force streaming behavior, try queries that:"
echo "   • Require multiple tool calls"
echo "   • Need step-by-step explanations"
echo "   • Involve complex data analysis"
echo "   • Take longer to process"
#!/usr/bin/env python3
"""
AWS Blockchain Data Processing Agent for AgentCore Deployment

Streamlined AgentCore-only implementation with async iterator streaming.
Specialized for analyzing Bitcoin, Ethereum, and TON blockchain data.
"""

from typing import Dict, Any, AsyncIterator
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient


# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Global agent instance
agent = None
mcp_client = None

#set system prompt globally
agent_instruction = """
Role: You are a blockchain data processing agent who can use AWS tools to identify schemas and generate SQL queries for Amazon Athena databases related to public blockchains, such as Bitcoin (btc), TON and Ethereum (eth) databases.

If you receive an ERROR from Athena, create another query to resolve the error message, and try to run it again. If there are 0 rows returned in the result set, specify that there were no results.

For blockchain data queries, you can use the AwsDataCatalog within the AWSPublicBlockchain workgroup in Athena.
Make sure that you properly return scientific notation values.

Example Databases and Tables:
- Bitcoin: blocks, transactions
- Ethereum: blocks, contracts, logs, token_transfers, traces, transactions
- TON: account_states, balances_history, blocks, dex_pools, dex_trades, jetton_events, jetton_metadata, messages_with_data, nft_events, nft_metadata, transactions

Objective: Identify schemas using schema discovery when required, and generate SQL queries based on the provided schema and user request. Return the response from the query.

Guidelines:
1. Query Decomposition and Understanding: Analyze the user's request to understand the main objective. Identify the blockchain. If unclear, ask for clarification.
   - For general requests (e.g., how many blocks are there), use a UNION.

2. SQL Query Creation: Use relevant fields from the schema.
   - Use btc for Bitcoin (btc.blocks) and eth for Ethereum (eth.logs). Bitcoin has array structures for inputs and outputs that require the UNNEST keyword. Do not use EXPLODE, this is not supported.
   - Cast varchar dates to date (e.g., cast(date_column as date)).
   - Use the date_add function to create timestamps for requested time ranges. To request a date of one day ago use date_add('day', -1, now()).
   - Ensure date comparisons use proper functions (e.g., date >= date_add('day', -30, current_date)).
   - **Always cast the date column to a date type in both the `SELECT` and `WHERE` clauses to avoid type mismatches (e.g., `cast(date as date)`).**
   - Determine the current date and time with the query.
   - Avoid mistakes: proper casting, correct prefixes, accurate syntax.

3. Query Execution and Response: Execute queries in Athena. Return results as fetched. Limit results to 20 to avoid memory issues.

4. For queries with a token_address, use the lower function on both sides of the equality check. For example if the address is '0xA0b86991', you would compare like this lower(token_address) = lower('0xA0b86991')

5. To check if an array contains an item, use the built-in function `contains`. For example, to check if the array 'products' contains an item called 'shoe', use this syntax: contains(products, 'shoe')

6. SQL array indices start at 1

**Ensure data integrity and accuracy. Always make sure to generate a query. Format the date parameter as instructed. Do not hallucinate.**
"""

def initialize_blockchain_agent():
    """Initialize the blockchain agent with MCP client."""
    global agent, mcp_client
    
    try:
        # Create MCP client for AWS data processing
        mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="uvx",
                args=["awslabs.aws-dataprocessing-mcp-server@latest"]
            )
        ))
        
        # Create an instance of BedrockModel to define foundation model and parameters
        bedrock_model = BedrockModel(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.0,
            top_p=1.0,
            cache_prompt="default" #cache system prompt with 5min TTL, reduces token usage for repeat prompts
        )
        
        # Create Strands agent with MCP client using Managed Integration
        # The agent will handle MCP connection lifecycle automatically
        agent = Agent(
            model=bedrock_model,
            tools=[mcp_client],  # Pass MCP client directly - managed integration
            name="AWS Blockchain Data Processing Assistant",
            system_prompt=agent_instruction
        )
        
        print("✅ Blockchain Agent initialized for AgentCore with managed MCP integration")
        
    except Exception as e:
        print(f"❌ Failed to initialize blockchain agent: {e}")
        import traceback
        traceback.print_exc()
        raise


# Initialize the agent on module load
initialize_blockchain_agent()


@app.entrypoint
async def invoke_streaming(payload):
    """
    Primary AgentCore entrypoint with async iterator streaming.
    
    Args:
        payload: Request payload from AgentCore
        
    Yields:
        Streaming response events
    """
    try:
        # Extract user prompt
        user_message = payload["prompt"]
        if not user_message:
            yield {
                "error": "No prompt found in input. Please provide a 'prompt' key in the input.",
                "status": "error"
            }
            return
        
        # Stream agent response - MCP lifecycle managed automatically by agent
        stream = agent.stream_async(user_message)
        async for event in stream:
            if "data" in event:
                yield event["data"]
            if "tool_use" in event:
                tool_info = event["tool_use"]
                tool_name = tool_info.get("name", "Unknown")
                tool_input = tool_info.get("input", {})

                # Format the tool call as a special marker that can be easily detected by the client
                yield "\n<tool_call>\n"
                yield f"name: {tool_name}\n"
                yield f"params: {tool_input}\n"
                yield "</tool_call>\n"
            if "tool_result" in event:
                # Optionally show tool results
                tool_result = event["tool_result"]
                yield "\n<tool_result>\n"
                yield f"status: {tool_result.get('status', 'completed')}\n"
                yield "</tool_result>\n"

                
    except Exception as e:
        yield {
            "error": f"Agent streaming failed: {str(e)}",
            "status": "error"
        }


if __name__ == "__main__":
    print("🚀 Starting AWS Blockchain Data Processing Agent for AgentCore...")
    app.run()

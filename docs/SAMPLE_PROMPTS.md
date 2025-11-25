# Blockchain Data Agent - Sample Prompts

This document provides sample prompts that work with the blockchain data agent for querying Bitcoin, Ethereum, and TON blockchain data from AWS Public Blockchain datasets.

## Table of Contents

- [Bitcoin (BTC) Prompts](#bitcoin-btc-prompts)
- [Ethereum (ETH) Prompts](#ethereum-eth-prompts)
- [TON (The Open Network) Prompts](#ton-the-open-network-prompts)
- [Cross-Chain Comparison Prompts](#cross-chain-comparison-prompts)
- [Time-Based Query Examples](#time-based-query-examples)
- [Advanced/Complex Prompts](#advancedcomplex-prompts)
- [Tips for Best Results](#tips-for-best-results)
- [Database Schema Reference](#database-schema-reference)

---

## Bitcoin (BTC) Prompts

### Block Analysis

- "How many Bitcoin blocks were created yesterday?"
- "Show me the latest 5 Bitcoin blocks with their timestamps"
- "What's the average block size for Bitcoin blocks created in the last 7 days?"
- "Find the block with the highest number of transactions this week"

### Transaction Analysis

- "How many Bitcoin transactions happened in the last 24 hours?"
- "What's the total transaction volume in Bitcoin over the past week?"
- "Show me the largest Bitcoin transaction from yesterday"
- "Find transactions with more than 10 inputs in the last hour"

### Network Activity

- "What's the average number of transactions per block today?"
- "Compare Bitcoin transaction volume between today and last week"
- "Show me Bitcoin network activity trends for the past month"

### Advanced Queries (Using UNNEST for arrays)

- "Find all transactions where the first output amount exceeds 1 BTC"
- "Show me transactions with more than 5 outputs from the last 24 hours"
- "What are the most common input counts in recent Bitcoin transactions?"

---

## Ethereum (ETH) Prompts

### Block Analysis

- "How many Ethereum blocks were mined in the last hour?"
- "What's the average gas used per block today?"
- "Show me the 10 most recent Ethereum blocks"
- "Find blocks with the highest gas limit from yesterday"

### Transaction Analysis

- "How many Ethereum transactions occurred in the last 24 hours?"
- "What's the average gas price for transactions today?"
- "Show me the highest value Ethereum transactions from this week"
- "Find failed transactions from the last hour"

### Smart Contract Activity

- "How many smart contract deployments happened today?"
- "Show me the most active smart contracts by transaction count this week"
- "Find contracts created in the last 24 hours"

### Token Transfers

- "Show me the top 10 USDC transfers over $1 million today"
- "How many USDC token transfers happened in the last hour?"
- "Find the largest token transfer for USDC this week"
- "What are the most active ERC-20 tokens by transfer count today?"

### Logs and Events

- "Show me the most common event signatures from the last hour"
- "Find all Transfer events for a specific contract address today"
- "How many log entries were created in the last 24 hours?"

### Traces (Internal Transactions)

- "Show me internal transactions with value greater than 10 ETH today"
- "Find all contract calls that failed in the last hour"
- "What are the most common trace types from yesterday?"

---

## TON (The Open Network) Prompts

### Block Analysis

- "How many TON blocks were created in the last hour?"
- "Show me the latest 10 TON blocks"
- "What's the average number of transactions per TON block today?"

### Transaction Analysis

- "How many TON transactions occurred in the last 24 hours?"
- "Show me the largest TON transactions by value from yesterday"
- "Find transactions with specific message types from the last hour"

### Account Activity

- "Show me the most active TON accounts by transaction count today"
- "Find accounts with balance changes greater than 1000 TON yesterday"
- "What are the account states for the top 5 accounts by balance?"

### Message Analysis

- "How many messages were sent on TON in the last hour?"
- "Show me messages with the highest value from today"
- "Find all messages between two specific accounts this week"

### Jetton (Token) Activity

- "Show me the most recent jetton transfer events"
- "How many jetton transfers happened in the last 24 hours?"
- "Find the most active jetton tokens by transfer count today"
- "Show me jetton metadata for the top 5 tokens"

### NFT Activity

- "How many NFT transfers occurred on TON today?"
- "Show me the most recent NFT events"
- "Find NFT collections with the most activity this week"
- "What are the metadata details for recent NFT transfers?"

### DEX Activity

- "Show me the most active DEX pools on TON today"
- "How many DEX trades happened in the last hour?"
- "Find the largest DEX trades by volume from yesterday"
- "What are the most traded token pairs on TON DEXes this week?"

---

## Cross-Chain Comparison Prompts

### General Comparisons

- "How many blocks were created across Bitcoin, Ethereum, and TON in the last hour?"
- "Compare transaction volumes between Bitcoin and Ethereum today"
- "Which blockchain had the most activity in the last 24 hours?"
- "Show me block creation rates for all three blockchains"

### Network Activity

- "Compare average transactions per block across all blockchains today"
- "Which blockchain processed the most transactions yesterday?"
- "Show me network activity trends for Bitcoin, Ethereum, and TON this week"

---

## Time-Based Query Examples

### Recent Activity (Last Hour)

- "Show me Bitcoin blocks from the last hour"
- "How many Ethereum transactions in the past 60 minutes?"
- "What's the TON network activity in the last hour?"

### Daily Analysis

- "Analyze Bitcoin transaction patterns for today"
- "Show me Ethereum gas usage trends for the current day"
- "What's the TON network summary for today?"

### Weekly Trends

- "Compare Bitcoin block production over the last 7 days"
- "Show me Ethereum token transfer trends for the past week"
- "What are the TON DEX trading patterns this week?"

### Monthly Overview

- "Give me a Bitcoin network summary for the last 30 days"
- "Show me Ethereum smart contract deployment trends this month"
- "What's the TON network growth over the past month?"

---

## Advanced/Complex Prompts

### Multi-Step Analysis

- "First check how many Bitcoin blocks were created today, then show me the average transaction count per block"
- "Find the most active Ethereum contract today, then show me all its transactions"
- "Identify the top TON DEX pool by volume, then show me its recent trades"

### Conditional Queries

- "Show me Ethereum transactions where gas price exceeded 100 gwei today"
- "Find Bitcoin transactions with more than 3 inputs and 3 outputs from yesterday"
- "List TON accounts where balance increased by more than 10% this week"

### Aggregation Queries

- "What's the total value transferred in USDC on Ethereum today?"
- "Calculate the average Bitcoin transaction size for the last 1000 blocks"
- "Sum up all TON jetton transfers for the past 24 hours"

### Error Recovery Examples

- "Show me Ethereum blocks from yesterday" *(if error, agent should retry with corrected query)*
- "Find Bitcoin transactions with amount greater than 100" *(agent should handle scientific notation)*
- "List TON messages from last week" *(agent should handle date casting properly)*

---

## Tips for Best Results

### 1. Be Specific with Time Ranges
Use clear time expressions like:
- "last 24 hours"
- "today"
- "yesterday"
- "last week"
- "past 30 days"

### 2. Use Proper Token Addresses
For token queries (especially USDC on Ethereum), the agent knows to use case-insensitive comparison:
```sql
lower(token_address) = lower('0xA0b86991...')
```

### 3. Result Limits
The agent automatically limits results to 20 rows to avoid memory issues. If you need more data, ask for specific subsets or aggregations.

### 4. Let the Agent Handle Errors
If a query fails with an Athena error, the agent will:
1. Analyze the error message
2. Create a corrected query
3. Retry automatically

### 5. Scientific Notation
The agent properly returns and formats scientific notation values for large numbers.

### 6. Date Handling
The agent automatically casts date columns properly to avoid type mismatches:
```sql
cast(date as date) >= date_add('day', -1, current_date)
```

### 7. Array Handling (Bitcoin)
Bitcoin data uses array structures for inputs and outputs. The agent uses `UNNEST` (not `EXPLODE`) to work with these arrays.

### 8. Schema Discovery
If you ask about fields the agent isn't sure about, it will use schema discovery tools to identify the correct column names and data types.

---

## Database Schema Reference

Your agent has access to these tables in the AWS Public Blockchain datasets:

### Bitcoin (btc)
- `btc.blocks` - Bitcoin block data
- `btc.transactions` - Bitcoin transaction data with array structures for inputs/outputs

### Ethereum (eth)
- `eth.blocks` - Ethereum block data
- `eth.contracts` - Smart contract deployments
- `eth.logs` - Event logs from smart contracts
- `eth.token_transfers` - ERC-20 and ERC-721 token transfers
- `eth.traces` - Internal transactions and contract calls
- `eth.transactions` - Ethereum transaction data

### TON (ton)
- `ton.account_states` - Account state information
- `ton.balances_history` - Historical balance changes
- `ton.blocks` - TON block data
- `ton.dex_pools` - DEX liquidity pool information
- `ton.dex_trades` - DEX trade history
- `ton.jetton_events` - Jetton (token) transfer events
- `ton.jetton_metadata` - Jetton token metadata
- `ton.messages_with_data` - Message data between accounts
- `ton.nft_events` - NFT transfer and mint events
- `ton.nft_metadata` - NFT collection and item metadata
- `ton.transactions` - TON transaction data

### Workgroup
All queries run in the `AWSPublicBlockchain` workgroup using the `AwsDataCatalog`.

---

## Example Interactions

### Simple Query
**You:** "How many Bitcoin blocks were created yesterday?"

**Agent:** 
```
Let me query the Bitcoin blockchain data for yesterday's blocks.

[Executes Athena query]
SELECT COUNT(*) as block_count 
FROM btc.blocks 
WHERE cast(date as date) = date_add('day', -1, current_date)

Result: 144 Bitcoin blocks were created yesterday.
```

### Complex Query with Tool Visualization
**You:** "Show me the top 5 USDC transfers over $1M today"

**Agent:**
```
I'll query the Ethereum token transfers for large USDC transactions today.

🔧 Tool Call:
  Tool: athena_query
  Parameters:
    • database: eth
    • query: SELECT transaction_hash, value, block_timestamp...

Result: Found 3 USDC transfers over $1M today:
1. $2,500,000 USDC at 2024-01-15 08:23:45
2. $1,800,000 USDC at 2024-01-15 12:15:30
3. $1,200,000 USDC at 2024-01-15 15:42:18
```

### Error Recovery
**You:** "Show me Ethereum blocks from last month"

**Agent:**
```
Let me query Ethereum blocks from the past month.

[First attempt fails with date type mismatch]

I encountered an error with the date comparison. Let me fix that and try again.

[Executes corrected query with proper date casting]
SELECT * FROM eth.blocks 
WHERE cast(date as date) >= date_add('day', -30, current_date)
LIMIT 20

Result: Here are the 20 most recent Ethereum blocks from the past month...
```

---

## Getting Started

To test these prompts with your agent:

### Using the CLI
```bash
python invoke_agent_async.py --agent-name blockchain_agent --region us-east-1
```

### Using Python SDK
```python
import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

response = client.invoke_agent_runtime(
    agentRuntimeArn='<your-agent-arn>',
    runtimeSessionId='<session-id>',
    payload=json.dumps({"prompt": "How many Bitcoin blocks yesterday?"})
)
```

### Using a Web UI
Deploy a Streamlit or React interface (see UI documentation) for a more interactive experience.

---

## Contributing

Have a great prompt that works well? Feel free to add it to this document!

## Support

For issues or questions:
- Check the agent logs in CloudWatch
- Review the Athena query history
- Ensure your IAM role has proper permissions for Athena and S3

---

**Last Updated:** January 2025
**Agent Version:** 1.0
**Supported Blockchains:** Bitcoin (BTC), Ethereum (ETH), TON

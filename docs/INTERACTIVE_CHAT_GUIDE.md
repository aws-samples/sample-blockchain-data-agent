# Interactive Chat Guide - invoke_agent_async.py

## Overview

The `invoke_agent_async.py` script provides an interactive chat interface for your deployed AgentCore blockchain agent. It automatically discovers the agent ARN based on the agent name.

## Features

✅ **Dynamic Agent Discovery** - Automatically fetches agent ARN by name  
✅ **Interactive Chat** - Real-time conversation with your agent  
✅ **Session Management** - Maintains conversation context  
✅ **Rich Console Output** - Color-coded, formatted responses  
✅ **Status Validation** - Checks if agent is ready before connecting  

## Installation

Ensure you have the required dependencies:

```bash
pip install boto3 rich
```

## Usage

### Basic Usage

```bash
python invoke_agent_async.py --agent-name blockchain_agent
```

### Specify Region

```bash
python invoke_agent_async.py --agent-name blockchain_agent --region us-west-2
```

### Using Environment Variables (Legacy)

```bash
export AGENT_NAME=blockchain_agent
export AWS_REGION=us-east-1
python invoke_agent_async.py
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--agent-name` | Name of the AgentCore agent | From `AGENT_NAME` env var |
| `--region` | AWS region | From `AWS_REGION` env var or `us-east-1` |

## Example Session

```bash
$ python invoke_agent_async.py --agent-name blockchain_agent

🔍 Looking up agent 'blockchain_agent'...
✅ Found agent with status: ACTIVE

Blockchain Data Agent Chat Interface
==================================================
Agent: blockchain_agent
Region: us-east-1
ARN: arn:aws:bedrock:us-east-1:123456789012:agent-runtime/ABCDEFGHIJ
Session ID: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0f
==================================================
Type 'quit', 'exit', or 'bye' to end the chat
==================================================

You: List all available databases

Agent: Based on the AWS Athena data catalog, here are the available databases:

1. **btc** - Bitcoin blockchain data
   - Tables: blocks, transactions
   
2. **eth** - Ethereum blockchain data
   - Tables: blocks, contracts, logs, token_transfers, traces, transactions
   
3. **ton** - TON blockchain data
   - Tables: account_states, blocks, messages_with_data, transactions

You: Show me the latest Bitcoin block

Agent: ⏳ Processing athena_query query... (10s elapsed)
⏳ Processing athena_query query... (20s elapsed)

Here's the latest Bitcoin block:

Block Number: 850123
Timestamp: 2024-11-13 15:30:45
Hash: 00000000000000000002a3b4c5d6e7f8...
Transactions: 2,847

You: quit

Goodbye!
```

## Exit Commands

Type any of these to end the chat session:
- `quit`
- `exit`
- `bye`
- `q`
- Press `Ctrl+C`

## How It Works

### 1. Agent Discovery

The script uses the AgentCore Control API to find your agent:

```python
# List all agents
response = control_client.list_agent_runtimes()

# Find agent by name
for agent in response.get('agentRuntimes', []):
    if agent.get('agentRuntimeName') == agent_name:
        # Get full details including ARN
        agent_info = control_client.get_agent_runtime(agentRuntimeId=agent_id)
        agent_arn = agent_info['agentRuntimeArn']
```

### 2. Session Management

Each chat session gets a unique session ID:

```python
session_id = str(uuid.uuid4()).replace("-", "")[:40] + "f"
```

This maintains conversation context across multiple messages.

### 3. Message Streaming

Messages are sent to the agent and responses are streamed back:

```python
response = agent_core_client.invoke_agent_runtime(
    agentRuntimeArn=agent_runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps({"prompt": user_input}),
    qualifier="DEFAULT"
)
```

### 4. Thinking Events

The agent emits thinking events during long-running queries:

```
⏳ Processing athena_query query... (10s elapsed)
⏳ Processing athena_query query... (20s elapsed)
```

These keep the connection alive and provide progress feedback.

## Troubleshooting

### Agent Not Found

```
❌ Agent 'blockchain_agent' not found
Available agents:
  • test_agent
  • demo_agent
```

**Solution**: Check the agent name spelling or use one of the listed agents.

### Agent Not Ready

```
⚠️  Warning: Agent status is 'CREATING', not 'ACTIVE' or 'READY'
```

**Solution**: Wait for the agent to finish provisioning. Check status with:

```bash
python deploy_with_docker.py --agent-name blockchain_agent --skip-test
```

### Connection Timeout

```
Error: Read timeout on endpoint URL
```

**Solution**: The agent might be processing a long query. The script has extended timeouts, but very long queries (>5 minutes) may still timeout. Try a simpler query first.

### AWS Credentials Error

```
Error: Unable to locate credentials
```

**Solution**: Configure AWS credentials:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

## Advanced Usage

### Custom Session ID

Modify the script to use a custom session ID for resuming conversations:

```python
# In __init__ method
self.session_id = "my-custom-session-id-12345678901234567890f"
```

### Logging Responses

Redirect output to a file:

```bash
python invoke_agent_async.py --agent-name blockchain_agent | tee chat_log.txt
```

### Batch Queries

Create a file with queries and pipe them:

```bash
cat queries.txt | python invoke_agent_async.py --agent-name blockchain_agent
```

Example `queries.txt`:
```
List databases
Show Bitcoin blocks from today
Count Ethereum transactions this week
quit
```

## Comparison with test_agent.py

| Feature | invoke_agent_async.py | test_agent.py |
|---------|----------------------|---------------|
| **Mode** | Interactive chat | Single query |
| **Session** | Persistent | One-time |
| **Context** | Maintains history | No history |
| **Use Case** | Exploration, testing | Automated testing |
| **Output** | Rich formatting | Plain text |

## Example Queries

### Database Exploration

```
You: List all available databases
You: Show me the schema for the eth.blocks table
You: What tables are in the Bitcoin database?
```

### Data Queries

```
You: Show me the latest 5 Bitcoin blocks
You: Count Ethereum transactions from today
You: Find the largest Bitcoin transaction this week
```

### Complex Analysis

```
You: Compare transaction volumes between Bitcoin and Ethereum today
You: Show me the most active Ethereum contracts this month
You: Analyze TON blockchain activity for the past 7 days
```

## Integration with Other Tools

### Use with Jupyter Notebooks

```python
import subprocess
import json

def query_agent(prompt, agent_name="blockchain_agent"):
    """Query the agent from a Jupyter notebook"""
    result = subprocess.run(
        ["python", "invoke_agent_async.py", "--agent-name", agent_name],
        input=f"{prompt}\nquit\n",
        capture_output=True,
        text=True
    )
    return result.stdout
```

### Use with CI/CD

```bash
# In your CI/CD pipeline
echo "List databases" | python invoke_agent_async.py --agent-name blockchain_agent
```

## Related Files

- **test_agent.py** - Single-query testing script
- **deploy_with_docker.py** - Agent deployment script
- **THINKING_EVENTS_GUIDE.md** - How thinking events work
- **QUICKSTART.md** - Getting started guide

## Summary

The interactive chat script provides a user-friendly way to explore your blockchain agent's capabilities. It automatically discovers your agent, maintains conversation context, and displays thinking events during long-running queries.

**Quick Start**:
```bash
python invoke_agent_async.py --agent-name blockchain_agent
```

Happy chatting! 🚀

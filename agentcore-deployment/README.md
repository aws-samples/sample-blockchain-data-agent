# Blockchain Data Processing Agent - AgentCore Deployment

The agentcore-deployment directory contains an implementation of the blockchain data analytics agent specifically designed for **Amazon Bedrock AgentCore deployment**. It uses indexed blockchain data in the AWS Public Blockchain datasets, but can be expanded to use a variety of data sources. 

## 🎯 Features

### ✅ **AgentCore SDK Integration**
- Uses `BedrockAgentCoreApp` for seamless AgentCore deployment
- Automatic HTTP server setup with `/invocations` and `/ping` endpoints
- Built-in deployment tools via AgentCore Starter Toolkit

### ✅ **Global Cross-Region Inference (CRIS)**
- Uses Claude Sonnet 4 with Global CRIS for higher throughput
- ~10% cost savings compared to regional inference
- Automatic routing to optimal AWS region globally
- Enhanced resilience during traffic spikes

### ✅ **Async Iterator Streaming**
- Real-time streaming responses using `agent.stream_async()`
- Efficient handling of large blockchain data queries
- Optimized for AgentCore's streaming architecture

### ✅ **Blockchain Intelligence**
- Specialized for Bitcoin (BTC), Ethereum (ETH), and TON blockchain data
- Advanced SQL query generation for blockchain datasets
- Proper handling of blockchain-specific data structures (arrays, scientific notation)


## 📁 File Structure

```
agentcore-deployment/
├── blockchain_agent_agentcore.py    # Main agent with AgentCore integration
├── deploy_blockchain_agent.py       # Automated deployment script using Docker and Boto3
├── requirements.txt                 # Python dependencies
├── agentcore_iam_policy.json        # IAM policy for AgentCore agent (includes Global CRIS)
├── agentcore_iam_role.json          # IAM role for AgentCore agent
├── deployment_user_iam_policy.json  # IAM policy for *user/role* deploying to AgentCore
├── invoke_agent_async.py            # Interactive chat interface to test the deployed agent
└── README.md                        # This documentation
```

### 1️⃣ Pre-requisites

- **Python 3.10+** (use `uv` or `pyenv` to manage Python versions)
- **Docker and Docker Buildx** (required to build and deploy the agent)
- **pip** (have a version of pip installed that's compatible with your Python version)
- **AWS CLI** (if developing locally, use `aws configure` to set up credentials)
- **AWS Bedrock model access** (use the AWS Console to enable the required foundation models, such as Claude Sonnet 4)
- **Boto3** (used in the deployment script)
 


## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd agentcore-deployment
pip install -r requirements.txt
```


### 2. Deploy to AgentCore

```bash
# Automated deployment with Docker and Boto3
python3 deploy_with_docker.py --agent-name "my_blockchain_data_agent" --region us-east-1

```

### 3. Test the Agent

```bash
# Test the deployed agent with an interactive chat interface
python3 invoke_agent_async.py --agent-name "my_blockchain_data_agent"
```

## 🏗️ Architecture

### AgentCore Integration Flow

```
User Request → AgentCore Runtime → SDK Integration → Blockchain Agent → MCP Server → AWS Services
```

### Streaming Architecture

```python
# AgentCore calls the streaming entrypoint
@app.entrypoint
async def invoke_streaming(payload):
    # Agent processes request with async streaming
    async for event in blockchain_agent.process_request_streaming(payload):
        yield event  # Real-time streaming to user
```

### MCP Server Integration via Strands

The MCP server connection in Strands is managed by the `MCPClient` class, which:

1. Establishes a connection to the MCP server using the provided transport
2. Initializes the MCP session
3. Discovers available tools
4. Handles tool invocation and result conversion
5. Manages the connection lifecycle


### Key Components

1. **BlockchainAgentCore Class**
   - Manages MCP client lifecycle
   - Provides sync and async processing methods
   - Handles blockchain-specific system prompts

2. **AgentCore Integration**
   - `BedrockAgentCoreApp` for HTTP server management
   - Dual entrypoints for sync and streaming modes
   - Automatic payload handling and response formatting

3. **MCP Integration**
   - AWS Data Processing MCP server for Athena queries
   - Schema discovery and SQL generation
   - Secure tool execution within context managers

## 🔍 Testing

### Local Testing Suite

The `test_agent_locally.py` script provides comprehensive testing:

```bash
python test_agent_locally.py
```

**Test Coverage:**
- ✅ Synchronous mode testing
- ✅ Async streaming mode testing
- ✅ Error handling validation
- ✅ AgentCore payload compatibility
- ✅ MCP server connectivity


## 📊 Example Usage

### Bitcoin Analysis
```json
{
  "prompt": "How many Bitcoin transactions happened in the last 24 hours?"
}
```

**Streaming Response:**
```
🤖 I'll query the Bitcoin transactions data for the last 24 hours.

[Executes Athena query]
SELECT COUNT(*) as transaction_count 
FROM btc.transactions 
WHERE cast(date as date) >= date_add('day', -1, current_date)

Result: 245,832 Bitcoin transactions occurred in the last 24 hours.
```

### Ethereum Token Analysis
```json
{
  "prompt": "Show me the top 10 USDC transfers over $1M today"
}
```

**Streaming Response:**
```
🤖 I'll analyze large USDC transfers on Ethereum for today.

[Executes optimized Athena query with proper token address handling]
SELECT transaction_hash, value, block_timestamp
FROM eth.token_transfers 
WHERE lower(token_address) = lower('0xA0b86991cC7aA037b92E4c2553451D454938AbD')
AND cast(value as double) > 1000000
AND cast(date as date) = current_date
ORDER BY cast(value as double) DESC
LIMIT 10

[Returns formatted results with scientific notation handling]
```

### TON DeFi Analysis
```json
{
  "prompt": "What are the most active TON DEX pools this week?"
}
```

### AgentCore Security

- **Session Isolation**: Each user session runs in dedicated microVMs
- **Credential Management**: Uses IAM roles for AWS service access
- **Network Security**: Configurable network modes (PUBLIC/PRIVATE)
- **Audit Trail**: All operations logged to CloudWatch

## 📈 Monitoring and Observability

### Built-in Monitoring

AgentCore provides automatic monitoring:
- **Metrics**: Request latency, error rates, token usage
- **Traces**: Distributed tracing with X-Ray integration
- **Logs**: Structured logging to CloudWatch

### Enable Enhanced Observability

1. **Install OpenTelemetry** (included in requirements.txt):
   ```bash
   pip install aws-opentelemetry-distro>=0.10.1
   ```

2. **Enable CloudWatch Transaction Search**:
   - Go to CloudWatch Console → Application Signals → Transaction Search
   - Enable Transaction Search with span ingestion

3. **Run with Auto-Instrumentation**:
   ```bash
   opentelemetry-instrument python blockchain_agent_agentcore.py
   ```

### View Observability Data

1. Open CloudWatch Console
2. Navigate to GenAI Observability
3. Find your agent service
4. View traces, metrics, and logs

## 🛠️ Troubleshooting

### Common Issues

#### 1. MCP Server Connection Failed
```bash
# Test MCP server availability
uvx awslabs.aws-dataprocessing-mcp-server@latest --help

# Install uv/uvx if missing
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. AWS Credentials Not Found
```bash
# Check credentials
aws sts get-caller-identity

# Configure if needed
aws configure
```

#### 3. AgentCore Deployment Failed
```bash
# Check starter toolkit installation
pip install bedrock-agentcore-starter-toolkit

# Verify AWS permissions
aws iam get-user
```

#### 4. Local Testing Requires Docker
```bash
# Install Docker, Finch, or Podman for local testing
# Or skip local testing:
python deploy_blockchain_agent.py --skip-local-test
```

### Error Resolution

**"No tools available from MCP server"**
- Check internet connection
- Verify uvx installation: `which uvx`
- Test MCP server manually: `uvx awslabs.aws-dataprocessing-mcp-server@latest --help`

**"Agent processing failed"**
- Check AWS credentials and permissions
- Verify Athena workgroup access
- Review CloudWatch logs for detailed errors

**"Deployment test failed"**
- Wait a few minutes for deployment to complete
- Check AgentCore Console for runtime status
- Verify agent name matches deployment

## 🔮 Advanced Configuration

### Custom System Prompts

Modify the `_get_blockchain_system_prompt()` method to customize the agent's behavior:

```python
def _get_blockchain_system_prompt(self) -> str:
    return """
    Your custom blockchain analysis instructions here...
    """
```

### Environment Variables

```bash
# AgentCore mode
export AGENTCORE_MODE=true

# AWS configuration
export AWS_DEFAULT_REGION=us-east-1
export AWS_PROFILE=blockchain-readonly

# Observability
export OTEL_SERVICE_NAME=my_blockchain_data_agent
export OTEL_RESOURCE_ATTRIBUTES=service.name=my_blockchain_data_agent
```

### Custom Deployment

For advanced deployment scenarios, use the manual boto3 approach:

```python
import boto3

client = boto3.client('bedrock-agentcore-control')
response = client.create_agent_runtime(
    agentRuntimeName='my_blockchain_data_agent-custom',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': 'your-ecr-repo/my_blockchain_data_agent:latest'
        }
    },
    networkConfiguration={"networkMode": "PUBLIC"},
    roleArn='arn:aws:iam::ACCOUNT:role/AgentCoreRole'
)
```

## 📚 Additional Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Strands Agents Documentation](https://strandsagents.com/)
- [AgentCore Starter Toolkit](https://pypi.org/project/bedrock-agentcore-starter-toolkit/)
- [AWS Public Blockchain Datasets](https://aws.amazon.com/blockchain/)

---

**Ready to deploy your blockchain data processing agent to AgentCore? Start with `python deploy_blockchain_agent.py`! 🚀**
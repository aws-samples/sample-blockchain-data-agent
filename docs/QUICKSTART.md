# Quick Start Guide - Docker Deployment with MCP Support

## What You're Deploying

A blockchain data processing agent that:
- Uses stdio MCP servers (with uvx support)
- Connects to AWS Data Processing MCP server
- Queries Bitcoin, Ethereum, and TON blockchain data
- Runs on AgentCore Runtime

## Prerequisites

```bash
# Check you have everything
docker --version          # Docker with buildx
aws --version            # AWS CLI
aws sts get-caller-identity  # AWS credentials configured
python3 --version        # Python 3.10+
```

## Deploy in 3 Steps

### Step 1: Install boto3
```bash
pip install boto3
```

### Step 2: Deploy
```bash
cd agentcore-deployment
python deploy_with_docker.py --agent-name "blockchain_agent" --region us-east-1
```

**Note**: Agent names must match pattern `[a-zA-Z][a-zA-Z0-9_]{0,47}` (letters, numbers, underscores only, max 48 chars). The script will automatically convert hyphens to underscores.

### Step 3: Test

**Option A: Single Query Test**
```bash
python test_agent.py --agent-name "blockchain_agent" --prompt "List all databases"
```

**Option B: Interactive Chat**
```bash
pip install rich  # If not already installed
python invoke_agent_async.py --agent-name "blockchain_agent"
```

The interactive chat provides:
- Real-time conversation with your agent
- Session context maintenance
- Thinking events during long queries
- Rich formatted output

## What Happens During Deployment

1. ✅ Checks prerequisites (Docker, AWS CLI, credentials)
2. ✅ Updates IAM policy with S3 bucket ARN
3. ✅ Creates/updates IAM role (AgentCoreDataProcessingRole)
4. ✅ Creates ECR repository
5. ✅ Builds ARM64 Docker image (using uv base image with uvx)
6. ✅ Pushes image to ECR
7. ✅ Deploys to AgentCore Runtime
8. ✅ Waits for agent to be ACTIVE
9. ✅ Tests with sample query

**Note:** The Dockerfile uses `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` which includes uvx pre-installed, making builds faster and more reliable.

## Expected Output

```
🚀 Blockchain Data Processing Agent - Docker Deployment to AgentCore
======================================================================
🔍 Checking prerequisites...
✅ AWS CLI: aws-cli/2.x.x
✅ AWS credentials configured (Account: 123456789012)
✅ Docker: Docker version 24.x.x
✅ Docker buildx available

📋 IAM Policy Update
------------------------------
✅ Updated policy with bucket: my-athena-results-bucket

🔐 IAM Role Setup
------------------------------
✅ IAM role AgentCoreDataProcessingRole already exists
✅ Attached/updated policy DataProcessingPolicy

📦 ECR Repository Setup
------------------------------
✅ ECR repository already exists: 123456789012.dkr.ecr.us-east-1.amazonaws.com/blockchain-agent

🐳 Docker Build & Push
------------------------------
🔐 Logging into ECR...
✅ Logged into ECR
🔨 Building Docker image (ARM64)...
✅ Built and pushed image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/blockchain-agent:latest

🚀 AgentCore Deployment
------------------------------
📝 Creating new agent...
✅ Created agent 'blockchain-agent'
📋 Agent Details:
   ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/blockchain-agent-abc123
   Status: CREATING

⏳ Agent Provisioning
------------------------------
⏳ Waiting for agent 'blockchain-agent' to be ready (max 15m)...
⏳ 0s - Status: CREATING
⏳ 30s - Status: CREATING
⏳ 60s - Status: ACTIVE
✅ Agent ready after 60s

🧪 Agent Testing
------------------------------
📤 Sending test query: List all available databases in the data catalog
✅ Agent responded successfully!
📋 Response preview: {'result': 'Available databases: btc, eth, ton'}...

🎉 Deployment Complete!
======================================================================
✅ Agent 'blockchain-agent' deployed to AgentCore
📋 Agent ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/blockchain-agent-abc123
🌍 Region: us-east-1
```

## Common Issues

### "Docker buildx not found"
```bash
docker buildx create --use
```

### "ECR login failed"
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
```

### "Agent not ready after 15m"
- Check AgentCore console for details
- Review CloudWatch logs
- Verify IAM permissions

## Next Steps

1. **Interactive Chat** (Recommended):
   ```bash
   pip install rich
   python invoke_agent_async.py --agent-name "blockchain_agent"
   ```
   
   Features:
   - Real-time conversation
   - Maintains context across queries
   - Shows thinking events during long operations
   - Rich formatted output
   
   See `INTERACTIVE_CHAT_GUIDE.md` for details.

2. **Test more queries**:
   ```bash
   python test_agent.py --agent-name "blockchain_agent" \
     --prompt "How many Bitcoin blocks were created today?"
   ```

3. **View logs**:
   ```bash
   aws logs tail /aws/bedrock-agentcore/blockchain_agent --follow
   ```

4. **Check status**:
   ```bash
   aws bedrock-agentcore-control get-agent-runtime \
     --agent-runtime-name blockchain_agent --region us-east-1
   ```

## Files You Need

- ✅ `deploy_with_docker.py` - Main deployment script
- ✅ `Dockerfile` - Container with uvx support
- ✅ `blockchain_agent_agentcore.py` - Agent code
- ✅ `requirements.txt` - Dependencies
- ✅ `agentcore_iam_policy.json` - IAM permissions
- ✅ `agentcore_iam_role.json` - IAM trust policy

All files are already in the `agentcore-deployment` directory!

## Help

For detailed documentation, see:
- `INTERACTIVE_CHAT_GUIDE.md` - Interactive chat usage
- `THINKING_EVENTS_GUIDE.md` - How thinking events prevent timeouts
- `DOCKER_DEPLOYMENT_README.md` - Complete deployment guide
- `AGENT_STATUS_GUIDE.md` - Agent lifecycle and status

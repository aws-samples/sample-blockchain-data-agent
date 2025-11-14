# Docker-Based AgentCore Deployment with MCP Support

This deployment approach uses Docker and boto3 to deploy your agent to AgentCore Runtime with full stdio MCP server support.

## Why This Approach?

The AgentCore Starter Toolkit doesn't provide control over the container build process, which means `uvx` isn't available for stdio MCP servers. This Docker-based approach:

✅ Properly installs `uvx` in the container
✅ Supports stdio MCP servers (like `awslabs.aws-dataprocessing-mcp-server`)
✅ Retains IAM policy management
✅ Uses boto3 for full deployment control
✅ Works with AgentCore Runtime

## Prerequisites

- Python 3.10+
- AWS CLI configured with credentials
- Docker with buildx support
- boto3 installed (`pip install boto3`)

## Quick Start

### 1. Install Dependencies

```bash
cd agentcore-deployment
pip install boto3
```

### 2. Deploy

```bash
python3 deploy_with_docker.py --agent-name "my-blockchain-agent" --region us-east-1
```

### 3. Test

The script automatically tests the agent. You can also test manually:

```python
import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

response = client.invoke_agent_runtime(
    agentRuntimeArn='<your-agent-arn>',
    runtimeSessionId='<33+-char-session-id>',
    payload=json.dumps({"prompt": "List all databases"}).encode('utf-8'),
    qualifier="DEFAULT"
)

result = json.loads(response['response'].read())
print(result)
```

## What the Script Does

### Step 1: Prerequisites Check
- Verifies AWS CLI, Docker, and Docker buildx
- Checks AWS credentials

### Step 2: IAM Setup
- Updates IAM policy with dynamic S3 bucket ARN
- Creates/updates `AgentCoreDataProcessingRole`
- Attaches data processing policy

### Step 3: ECR Repository
- Creates ECR repository if it doesn't exist
- Returns repository URI for image push

### Step 4: Docker Build & Push
- Builds ARM64 Docker image with uvx support
- Logs into ECR
- Pushes image to ECR

### Step 5: AgentCore Deployment
- Creates or updates agent runtime
- Configures with Docker image URI
- Sets up networking and IAM role

### Step 6: Readiness Check
- Waits for agent to become ACTIVE
- Monitors provisioning status
- Times out after 15 minutes

### Step 7: Testing
- Invokes agent with test query
- Verifies MCP tools are working
- Displays response

## Command-Line Options

```bash
python deploy_with_docker.py \
  --agent-name "my-agent" \          # Agent name (default: blockchain-data-agent)
  --region "us-east-1" \             # AWS region (default: us-east-1)
  --repository-name "my-repo" \      # ECR repo name (default: blockchain-agent)
  --skip-test                        # Skip agent testing
```

## Deployment on AWS Cloudshell or other non-ARM64 machines

### Step 1: Install Docker and Buildx

```
sudo dnf update -y
# Remove old version
sudo dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
# Install dnf plugin
sudo dnf -y install dnf-plugins-core
# Add CentOS repository
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
# Adjust release server version in the path as it will not match with Amazon Linux 2023
sudo sed -i 's/$releasever/9/g' /etc/yum.repos.d/docker-ce.repo
# Install as usual
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Step 2: Set up Buildx Builder for cross-platform builds

```
# Install Quick EMUlator (QEMU) binfmt handlers
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Verify QEMU is registered
ls /proc/sys/fs/binfmt_misc/ | grep qemu


# Create new builder with explicit platform support
docker buildx create --name multiarch --driver docker-container --platform linux/amd64,linux/arm64 --use

# Bootstrap (downloads buildkit)
docker buildx inspect --bootstrap

#once these steps are complete, you can run the Docker deployment script
```

## Files Used

### Required Files
- `blockchain_agent_agentcore.py` - Agent code with MCP client
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container definition with uvx
- `agentcore_iam_policy.json` - IAM permissions
- `agentcore_iam_role.json` - IAM trust policy
- `deploy_with_docker.py` - Deployment script

### Generated During Deployment
- ECR repository
- Docker image in ECR
- AgentCore agent runtime
- IAM role and policy

## Dockerfile Details

The Dockerfile uses uv's official base image which includes uvx:

```dockerfile
# Use uv's official ARM64 Python base image (includes uvx)
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Verify uvx is available (already included in base image)
RUN uvx --version

# Install dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt
```

This allows the MCP client to use:
```python
StdioServerParameters(
    command="uvx",
    args=["awslabs.aws-dataprocessing-mcp-server@latest"]
)
```

**Benefits of using the official uv base image:**
- ✅ uvx pre-installed and in PATH
- ✅ Faster builds (no curl installation needed)
- ✅ Smaller image size
- ✅ Official support from Astral (uv maintainers)

## Troubleshooting

### Docker Build Fails
- Ensure Docker is running
- Check Docker buildx: `docker buildx ls`
- Try: `docker buildx create --use`

### ECR Push Fails
- Verify AWS credentials
- Check ECR permissions
- Ensure region is correct

### Agent Deployment Fails
- Check IAM role permissions
- Verify image URI is correct
- Review CloudWatch logs

### Agent Not Ready
- Wait longer (can take 5-10 minutes)
- Check AgentCore console
- Review agent status in AWS console

### MCP Server Fails
- Verify uvx is in container: `docker run <image> uvx --version`
- Check MCP server package name
- Review agent logs in CloudWatch

## Updating Your Agent

To update an existing agent:

```bash
# Make code changes
# Run deployment again - it will update the existing agent
python deploy_with_docker.py --agent-name "my-agent"
```

The script automatically detects existing agents and updates them.

## Comparison with Starter Toolkit

| Feature | Starter Toolkit | Docker Deployment |
|---------|----------------|-------------------|
| Ease of use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| MCP stdio support | ❌ | ✅ |
| Container control | ❌ | ✅ |
| IAM management | ✅ | ✅ |
| Custom dependencies | Limited | Full control |
| Deployment speed | Fast | Moderate |

## Next Steps

After successful deployment:

1. **Monitor**: Check CloudWatch logs for agent activity
2. **Test**: Run various blockchain queries
3. **Optimize**: Adjust IAM permissions as needed
4. **Scale**: AgentCore handles scaling automatically
5. **Observe**: Enable CloudWatch Application Signals for metrics

## Additional Resources

- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Strands Agents Docs](https://strandsagents.com/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Docker Buildx](https://docs.docker.com/buildx/)

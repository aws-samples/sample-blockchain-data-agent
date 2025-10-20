# Blockchain Data Processing Agent with Strands Agents on AWS

This project demonstrates how to build an intelligent blockchain data analysis agent using the [Strands Agents](https://strandsagents.com) framework with the Model Context Protocol (MCP) to integrate with the `awslabs.aws-dataprocessing-mcp-server`.

## 🚀 Features

- **Intelligent AWS Data Processing**: Leverage AI to help with AWS data processing tasks
- **MCP Integration**: Seamlessly connect to awslabs.aws-dataprocessing-mcp-server tools
- **Structured Output**: Get organized analysis of data processing tasks
- **Interactive Chat**: Natural language interface for AWS operations
- **Direct Tool Access**: Call AWS tools directly when needed
- **Conversation Management**: Smart context management for long conversations

## 🚀 Quick Start: Amazon Bedrock AgentCore Deployment

### Pre-requisites

- **Python 3.10+** (use `uv` or `pyenv` to manage Python versions)
- **pip** (have a version of pip installed that's compatible with your Python version)
- **AWS CLI** (if developing locally, use `aws configure` to set up credentials)
- **AWS Bedrock model access** (use the AWS Console to enable the required foundation models, such as Claude Sonnet 4)

### 1. Install Dependencies

```bash
cd agentcore-deployment
pip install -r requirements.txt
```

### 2. Deploy to AgentCore

```bash
# Automated deployment with starter toolkit
python3 deploy_blockchain_agent.py --agent-name "my_blockchain_data_agent" --skip-local-test

# Or deploy manually (see Manual Deployment section)
```

### 3. Test Deployment

```bash
# Test the deployed agent
agentcore invoke --agent "my_blockchain_data_agent" '{"prompt": "How many Bitcoin blocks have been mined today?"}' 
```

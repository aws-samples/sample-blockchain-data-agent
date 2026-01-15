# Blockchain Data Processing Agent with Strands Agents on AWS

This project demonstrates how to build an intelligent blockchain data analysis agent using the [Strands Agents](https://strandsagents.com) framework with the Model Context Protocol (MCP) to integrate with the `awslabs.aws-dataprocessing-mcp-server`.

## 📁 Project Structure

```
├── agentcore-deployment/     # Agent deployment to Amazon Bedrock AgentCore
│   ├── blockchain_agent_agentcore.py
│   ├── deploy_blockchain_agent.py
│   ├── invoke_agent_async.py
│   └── ...
├── docs/                     # Documentation
│   ├── DOCKER_DEPLOYMENT_README.md
│   ├── SAMPLE_PROMPTS.md
│   ├── architecture-diagram.md
│   └── ...
└── utils/                    # Utility scripts
    ├── mcp_utils.py
    └── ...
```

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
- **Amazon Bedrock model access** (use the AWS Console to enable the required foundation models, such as Claude Sonnet 4)
- **Docker** installed with Buildx add-on
- **Blockchain Data Consumer Architecture** deployed to give your agent access to data from the [AWS Public Blockchain Datasets](https://registry.opendata.aws/aws-public-blockchain/) (see step 0. below)

### 0. Deploy the Blockchain Data Consumer Architecture via CloudFormation (Separate Repo)

```bash
# Clone the sample-public-blockchain-data-consumer repository
git clone https://github.com/aws-samples/sample-public-blockchain-data-consumer.git
cd sample-public-blockchain-data-consumer

# Deploy data infrastructure to give your agent access to data from the AWS Public Blockchain Datasets
aws cloudformation create-stack \
  --stack-name blockchain-crawlers \
  --template-body file://aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-create-complete --stack-name blockchain-crawlers
```

See [Public Blockchain Data Consumer Stack Documentation](https://github.com/aws-samples/sample-public-blockchain-data-consumer/blob/main/README.md) for detailed configuration options.

### 1. Install Dependencies

```bash
cd agentcore-deployment
pip install -r requirements.txt
```

### 2. Deploy to AgentCore

```bash
# Automated deployment with Docker
python3 deploy_blockchain_agent.py --agent-name "my_blockchain_data_agent" --region us-east-1


```

### 3. Test Deployment

```bash
# Test the deployed agent using interactive CLI utility
python3 invoke_agent_async.py --agent-name "my_blockchain_data_agent"
```

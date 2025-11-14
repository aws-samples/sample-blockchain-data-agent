#!/usr/bin/env python3
"""
Docker-based deployment script for Blockchain Data Processing Agent to AgentCore.

This script uses boto3 to:
1. Create/update IAM roles and policies
2. Build and push Docker image to ECR
3. Deploy agent to AgentCore Runtime

Supports stdio MCP servers via proper uvx installation in Dockerfile.
"""

import os
import sys
import subprocess
import argparse
import json
import time
import boto3
from pathlib import Path


def check_prerequisites():
    """Check if all prerequisites are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check AWS CLI
    try:
        result = subprocess.run(
            ["aws", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"✅ AWS CLI: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ AWS CLI not found. Please install AWS CLI and configure credentials.")
        return False
    
    # Check AWS credentials
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        identity = json.loads(result.stdout)
        print(f"✅ AWS credentials configured (Account: {identity['Account']})")
    except subprocess.CalledProcessError:
        print("❌ AWS credentials not configured. Please run 'aws configure'")
        return False
    
    # Check Docker
    try:
        result = subprocess.run(
            ["docker", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"✅ Docker: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker not found. Please install Docker.")
        return False
    
    # Check Docker buildx
    try:
        subprocess.run(
            ["docker", "buildx", "version"], 
            capture_output=True, 
            check=True
        )
        print("✅ Docker buildx available")
    except subprocess.CalledProcessError:
        print("⚠️  Docker buildx not available, attempting to create...")
        try:
            subprocess.run(["docker", "buildx", "create", "--use"], check=True)
            print("✅ Docker buildx created")
        except subprocess.CalledProcessError:
            print("❌ Failed to create Docker buildx")
            return False
    
    return True


def update_policy_with_dynamic_bucket():
    """Find S3 bucket and replace placeholder ARN in IAM policy."""
    print("🔍 Updating IAM policy with dynamic S3 bucket ARN...")
    
    try:
        s3_client = boto3.client('s3')
        buckets = s3_client.list_buckets()
        
        target_bucket = next((b['Name'] for b in buckets['Buckets'] 
                             if 'athenaresultsbucket' in b['Name'].lower()), None)
        
        if not target_bucket:
            print("⚠️  No bucket found with pattern 'athenaresultsbucket'")
            print("💡 Using placeholder - update manually if needed")
            return True
        
        # Update policy file
        policy_path = 'agentcore_iam_policy.json'
        with open(policy_path, 'r') as f:
            policy_text = f.read()
        
        # Replace placeholder with actual bucket name
        updated_policy = policy_text.replace('PLACEHOLDER_ATHENA_RESULTS_BUCKET', target_bucket)
        
        with open(policy_path, 'w') as f:
            f.write(updated_policy)
        
        print(f"✅ Updated policy with bucket: {target_bucket}")
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to update policy: {e}")
        print("💡 Continuing with placeholder - update manually if needed")
        return True


def ensure_iam_role_exists():
    """Ensure the AgentCore IAM role exists with proper permissions."""
    print("🔐 Ensuring IAM role exists with proper permissions...")
    
    try:
        iam = boto3.client('iam')
        sts = boto3.client('sts')
        
        # Get account ID
        account_id = sts.get_caller_identity()['Account']
        role_name = 'AgentCoreDataProcessingRole'
        policy_name = 'DataProcessingPolicy'
        
        # Check if role exists
        try:
            role = iam.get_role(RoleName=role_name)
            print(f"✅ IAM role {role_name} already exists")
            role_arn = role['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            # Create role with trust policy
            print(f"📝 Creating IAM role {role_name}...")
            
            # Read trust policy
            with open('agentcore_iam_role.json', 'r') as f:
                trust_policy = f.read()
            
            role_response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=trust_policy,
                Description="IAM role for AgentCore blockchain data processing agent"
            )
            role_arn = role_response['Role']['Arn']
            print(f"✅ Created IAM role {role_name}")
        
        # Attach/update policy
        print(f"📝 Updating policy {policy_name}...")
        
        # Read policy document
        with open('agentcore_iam_policy.json', 'r') as f:
            policy_document = f.read()
        
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document
        )
        print(f"✅ Attached/updated policy {policy_name} to role {role_name}")
        
        return role_arn
        
    except Exception as e:
        print(f"❌ Failed to ensure IAM role exists: {e}")
        return None


def create_ecr_repository(repository_name: str, region: str):
    """Create ECR repository if it doesn't exist."""
    print(f"📦 Creating ECR repository '{repository_name}'...")
    
    try:
        ecr = boto3.client('ecr', region_name=region)
        
        # Check if repository exists
        try:
            response = ecr.describe_repositories(repositoryNames=[repository_name])
            repo_uri = response['repositories'][0]['repositoryUri']
            print(f"✅ ECR repository already exists: {repo_uri}")
            return repo_uri
        except ecr.exceptions.RepositoryNotFoundException:
            # Create repository
            response = ecr.create_repository(
                repositoryName=repository_name,
                imageScanningConfiguration={'scanOnPush': True},
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            repo_uri = response['repository']['repositoryUri']
            print(f"✅ Created ECR repository: {repo_uri}")
            return repo_uri
            
    except Exception as e:
        print(f"❌ Failed to create ECR repository: {e}")
        return None


def build_and_push_docker_image(repository_uri: str, region: str, tag: str = "latest"):
    """Build Docker image and push to ECR."""
    print(f"🐳 Building and pushing Docker image...")
    
    try:
        # Get ECR login
        print("🔐 Logging into ECR...")
        ecr = boto3.client('ecr', region_name=region)
        auth_token = ecr.get_authorization_token()
        
        # Decode the authorization token
        import base64
        auth_token_decoded = base64.b64decode(
            auth_token['authorizationData'][0]['authorizationToken']
        ).decode('utf-8')
        username, password = auth_token_decoded.split(':', 1)
        
        registry = auth_token['authorizationData'][0]['proxyEndpoint']
        
        # Docker login
        subprocess.run([
            "docker", "login",
            "--username", username,
            "--password-stdin",
            registry
        ], input=password.encode(), check=True, capture_output=True)
        
        print("✅ Logged into ECR")
        
        # Build image
        print("🔨 Building Docker image (ARM64)...")
        image_tag = f"{repository_uri}:{tag}"
        
        subprocess.run([
            "docker", "buildx", "build",
            "--platform", "linux/arm64",
            "-t", image_tag,
            "--push",
            "."
        ], check=True)
        
        print(f"✅ Built and pushed image: {image_tag}")
        return image_tag
        
    except Exception as e:
        print(f"❌ Failed to build/push Docker image: {e}")
        import traceback
        traceback.print_exc()
        return None


def deploy_to_agentcore(agent_name: str, image_uri: str, role_arn: str, region: str):
    """Deploy agent to AgentCore Runtime."""
    print(f"🚀 Deploying agent '{agent_name}' to AgentCore Runtime...")
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        # Try to create first - simpler and handles most cases
        try:
            print(f"📝 Creating agent '{agent_name}'...")
            response = client.create_agent_runtime(
                agentRuntimeName=agent_name,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': image_uri
                    }
                },
                networkConfiguration={"networkMode": "PUBLIC"},
                roleArn=role_arn
            )
            print(f"✅ Created agent '{agent_name}'")
            
        except client.exceptions.ConflictException:
            # Agent already exists - find it and update
            print(f"⚠️  Agent '{agent_name}' already exists, updating...")
            
            # List all agents to find the existing one
            list_response = client.list_agent_runtimes()
            agent_id = None
            
            # The API returns 'agentRuntimes' not 'agentRuntimeSummaries'
            agents = list_response.get('agentRuntimes', [])
            print(f"🔍 Searching for agent in {len(agents)} agents...")
            
            for agent in agents:
                agent_runtime_name = agent.get('agentRuntimeName', '')
                print(f"   Checking: '{agent_runtime_name}' == '{agent_name}' ? {agent_runtime_name == agent_name}")
                if agent_runtime_name == agent_name:
                    agent_id = agent['agentRuntimeId']
                    print(f"✅ Found agent ID: {agent_id}")
                    break
            
            if not agent_id:
                # Try with pagination if there are more agents
                print(f"⚠️  Agent not found in first page, checking if there's pagination...")
                if 'nextToken' in list_response:
                    print(f"📄 Fetching more agents...")
                    list_response = client.list_agent_runtimes(nextToken=list_response['nextToken'])
                    for agent in list_response.get('agentRuntimes', []):
                        if agent.get('agentRuntimeName') == agent_name:
                            agent_id = agent['agentRuntimeId']
                            break
            
            if not agent_id:
                print(f"❌ Could not find agent '{agent_name}' in list")
                print(f"💡 Available agents:")
                list_response = client.list_agent_runtimes()
                for agent in list_response.get('agentRuntimes', [])[:10]:
                    print(f"   - {agent.get('agentRuntimeName')} (ID: {agent.get('agentRuntimeId')})")
                raise Exception(f"Agent '{agent_name}' exists but could not be found in list. Try deleting it first or use a different name.")
            
            # Update the existing agent
            print(f"🔄 Updating agent {agent_id}...")
            response = client.update_agent_runtime(
                agentRuntimeId=agent_id,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': image_uri
                    }
                },
                roleArn=role_arn,
                networkConfiguration={"networkMode": "PUBLIC"}
            )
            print(f"✅ Updated agent '{agent_name}'")
        
        agent_arn = response['agentRuntimeArn']
        agent_id = response['agentRuntimeId']
        status = response['status']
        
        print(f"📋 Agent Details:")
        print(f"   Name: {agent_name}")
        print(f"   ID: {agent_id}")
        print(f"   ARN: {agent_arn}")
        print(f"   Status: {status}")
        
        return agent_id, agent_arn
        
    except Exception as e:
        print(f"❌ Failed to deploy to AgentCore: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def wait_for_agent_ready(agent_id: str, region: str, max_minutes: int = 15):
    """Wait for agent to be ready."""
    print(f"⏳ Waiting for agent to be ready (max {max_minutes}m)...")
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        
        for elapsed in range(0, max_minutes * 60, 30):
            try:
                response = client.get_agent_runtime(agentRuntimeId=agent_id)
                status = response['status']
                
                # Check if agent is ready (ACTIVE or READY status)
                if status in ['ACTIVE', 'READY']:
                    print(f"✅ Agent ready after {elapsed}s (Status: {status})")
                    return True
                elif status in ['FAILED', 'STOPPED', 'DELETING']:
                    print(f"❌ Agent in failed state: {status}")
                    return False
                
                print(f"⏳ {elapsed}s - Status: {status}")
                time.sleep(30)
                
            except Exception as e:
                print(f"⚠️  Status check error: {e}")
                time.sleep(30)
        
        print(f"❌ Timeout after {max_minutes}m")
        return False
        
    except Exception as e:
        print(f"❌ Failed to check agent status: {e}")
        return False


def test_agent(agent_id: str, agent_arn: str, region: str):
    """Test the deployed agent with streaming support."""
    print(f"🧪 Testing agent...")
    
    try:
        # Configure boto3 client with extended timeout for long-running queries
        from botocore.config import Config
        config = Config(
            read_timeout=300,  # 5 minutes for long Athena queries
            connect_timeout=10
        )
        client = boto3.client('bedrock-agentcore', region_name=region, config=config)
        
        # Generate session ID (must be 33+ characters)
        import uuid
        session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]
        
        # Test query
        test_prompt = "List all available databases in the data catalog"
        payload = json.dumps({"prompt": test_prompt})
        
        print(f"📤 Sending test query: {test_prompt}")
        print(f"⏱️  Timeout configured: 300s (5 minutes)")
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=session_id,
            payload=payload.encode('utf-8'),
            qualifier="DEFAULT"
        )
        
        # Handle streaming response
        print("🌊 Reading streaming response...")
        complete_response = ""
        chunk_count = 0
        
        for chunk in response['response']:
            chunk_count += 1
            if isinstance(chunk, bytes):
                chunk_text = chunk.decode('utf-8')
                complete_response += chunk_text
                # Print first few chunks to show progress
                if chunk_count <= 5:
                    preview = chunk_text[:50].replace('\n', ' ')
                    print(f"  Chunk {chunk_count}: {preview}{'...' if len(chunk_text) > 50 else ''}")
        
        print(f"\n✅ Agent responded successfully!")
        print(f"📋 Received {chunk_count} chunks, total length: {len(complete_response)} chars")
        
        # Show a preview of the response
        if complete_response:
            preview = complete_response[:200].replace('\n', ' ')
            print(f"📄 Response preview: {preview}{'...' if len(complete_response) > 200 else ''}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(
        description="Deploy Blockchain Data Processing Agent to AgentCore with Docker"
    )
    parser.add_argument(
        "--agent-name", 
        default="blockchain_data_agent",
        help="Name for the AgentCore agent (default: blockchain_data_agent). Must match [a-zA-Z][a-zA-Z0-9_]{0,47}"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--repository-name",
        default="blockchain-agent",
        help="ECR repository name (default: blockchain-agent)"
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip testing the deployed agent"
    )
    
    args = parser.parse_args()
    
    # Validate and fix agent name (must match: [a-zA-Z][a-zA-Z0-9_]{0,47})
    original_name = args.agent_name
    # Replace hyphens with underscores, remove invalid characters
    fixed_name = original_name.replace('-', '_')
    fixed_name = ''.join(c for c in fixed_name if c.isalnum() or c == '_')
    # Ensure it starts with a letter
    if fixed_name and not fixed_name[0].isalpha():
        fixed_name = 'agent_' + fixed_name
    # Truncate to 48 characters
    fixed_name = fixed_name[:48]
    
    if fixed_name != original_name:
        print(f"⚠️  Agent name '{original_name}' contains invalid characters")
        print(f"   Using sanitized name: '{fixed_name}'")
        args.agent_name = fixed_name
    
    print("🚀 Blockchain Data Processing Agent - Docker Deployment to AgentCore")
    print("=" * 70)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Update IAM policy with dynamic bucket
    print("\n📋 IAM Policy Update")
    print("-" * 30)
    update_policy_with_dynamic_bucket()
    
    # Ensure IAM role exists
    print("\n🔐 IAM Role Setup")
    print("-" * 30)
    role_arn = ensure_iam_role_exists()
    if not role_arn:
        print("❌ IAM role setup failed.")
        sys.exit(1)
    
    # Create ECR repository
    print("\n📦 ECR Repository Setup")
    print("-" * 30)
    repository_uri = create_ecr_repository(args.repository_name, args.region)
    if not repository_uri:
        print("❌ ECR repository creation failed.")
        sys.exit(1)
    
    # Build and push Docker image
    print("\n🐳 Docker Build & Push")
    print("-" * 30)
    image_uri = build_and_push_docker_image(repository_uri, args.region)
    if not image_uri:
        print("❌ Docker build/push failed.")
        sys.exit(1)
    
    # Deploy to AgentCore
    print("\n🚀 AgentCore Deployment")
    print("-" * 30)
    agent_id, agent_arn = deploy_to_agentcore(args.agent_name, image_uri, role_arn, args.region)
    if not agent_id or not agent_arn:
        print("❌ AgentCore deployment failed.")
        sys.exit(1)
    
    # Wait for agent to be ready
    print("\n⏳ Agent Provisioning")
    print("-" * 30)
    if not wait_for_agent_ready(agent_id, args.region):
        print("⚠️  Agent may not be fully ready. Check AgentCore console.")
    
    # Test agent
    if not args.skip_test:
        print("\n🧪 Agent Testing")
        print("-" * 30)
        test_agent(agent_id, agent_arn, args.region)
    
    print("\n🎉 Deployment Complete!")
    print("=" * 70)
    print(f"✅ Agent '{args.agent_name}' deployed to AgentCore")
    print(f"📋 Agent ARN: {agent_arn}")
    print(f"🌍 Region: {args.region}")
    print(f"\n📋 Next Steps:")
    print(f"   • Test via AWS Console or boto3")
    print(f"   • View logs in CloudWatch")
    print(f"   • Monitor in AgentCore Console")


if __name__ == "__main__":
    main()

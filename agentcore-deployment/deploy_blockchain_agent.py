#!/usr/bin/env python3
"""
Deployment script for the Blockchain Data Processing Agent to Amazon Bedrock AgentCore.

This script automates the deployment process using the AgentCore Starter Toolkit
for quick and easy deployment with minimal configuration.
"""

import os
import sys
import subprocess
import argparse
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
        print("✅ AWS credentials configured")
    except subprocess.CalledProcessError:
        print("❌ AWS credentials not configured. Please run 'aws configure'")
        return False
    
    return True


def update_policy_with_dynamic_bucket():
    """Find S3 bucket and replace placeholder ARN in IAM policy."""
    print("🔍 Updating IAM policy with dynamic S3 bucket ARN...")
    
    try:
        import boto3
        
        # Find bucket
        s3_client = boto3.client('s3')
        buckets = s3_client.list_buckets()
        
        target_bucket = next((b['Name'] for b in buckets['Buckets'] 
                             if 'athenaresultsbucket' in b['Name']), None)
        
        if not target_bucket:
            print("❌ No bucket found with pattern 'athenaresultsbucket'")
            print("💡 Make sure the Athena results bucket exists in your AWS account")
            return False
        
        # Update policy file
        policy_path = 'agentcore_iam_policy.json'
        with open(policy_path, 'r') as f:
            policy_text = f.read()
        
        # Replace placeholder with actual bucket name
        updated_policy = policy_text.replace('PLACEHOLDER_ATHENA_RESULTS_BUCKET', target_bucket)
        
        with open(policy_path, 'w') as f:
            f.write(updated_policy)
        
        print(f"✅ Updated policy with bucket: {target_bucket}")
        print(f"   ARN: arn:aws:s3:::{target_bucket}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update policy: {e}")
        return False


def ensure_iam_role_exists():
    """Ensure the AgentCore IAM role exists with proper permissions."""
    import boto3
    import json
    
    print("🔧 Ensuring IAM role exists with proper permissions...")
    
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
            try:
                with open('agentcore_iam_role.json', 'r') as f:
                    trust_policy = f.read()
            except FileNotFoundError:
                # Default trust policy for AgentCore
                trust_policy = json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "bedrock-agentcore.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                })
            
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


def configure_agent(agent_name: str, role_arn: str = None):
    """Configure the agent for deployment."""
    print(f"⚙️ Configuring agent '{agent_name}'...")
    
    try:
        # Configure the agent with the starter toolkit
        configure_cmd = [
            "agentcore", "configure", 
            "--entrypoint", "blockchain_agent_agentcore.py",
            "--name", agent_name, "--non-interactive"
        ]
        
        # Add role ARN if provided
        if role_arn:
            configure_cmd.extend(["-er", role_arn])
            print(f"🔐 Using IAM role: {role_arn}")
        
        subprocess.run(configure_cmd, check=True)
        
        print(f"✅ Agent '{agent_name}' configured successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to configure agent: {e}")
        return False


def test_locally(agent_name: str):
    """Test the agent locally before deployment."""
    print(f"🧪 Testing agent '{agent_name}' locally...")
    
    try:
        # Launch local test (requires Docker/Finch/Podman)
        print("📦 Starting local container test...")
        subprocess.run([
            "agentcore", "launch", "--local", "--name", agent_name
        ], check=True)
        
        print("✅ Local test completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Local test failed (this is optional): {e}")
        print("💡 You can skip local testing and deploy directly to AWS")
        return False


def deploy_to_aws(agent_name: str):
    """Deploy the agent to AWS AgentCore."""
    print(f"🚀 Deploying agent '{agent_name}' to AWS AgentCore...")
    
    try:
        # Deploy to AWS
        subprocess.run([
            "agentcore", "launch", "--agent", agent_name
        ], check=True)
        
        print(f"✅ Agent '{agent_name}' deployed successfully to AWS AgentCore")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to deploy agent: {e}")
        return False


def test_deployment(agent_name: str):
    """Test the deployed agent with comprehensive permission checks."""
    print(f"🔬 Testing deployed agent '{agent_name}'...")
    
    # Test 1: Schema discovery (should work with read permissions)
    print("\n📋 Test 1: Schema Discovery")
    schema_payload = '{"prompt": "List all available databases in the data catalog"}'
    
    try:
        result = subprocess.run([
            "agentcore", "invoke", "--agent", agent_name, schema_payload
        ], capture_output=True, text=True, check=True)
        
        if "error" in result.stdout.lower() or "access denied" in result.stdout.lower():
            print("❌ Schema discovery test failed - permission issues")
            print(f"Response: {result.stdout}")
            return False
        else:
            print("✅ Schema discovery test passed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Schema discovery test failed: {e}")
        return False
    
    # Test 2: Query execution (requires StartQueryExecution permission)
    print("\n📋 Test 2: Query Execution")
    query_payload = '{"prompt": "SELECT COUNT(*) as block_count FROM btc.blocks WHERE cast(date as date) = current_date LIMIT 1"}'
    
    try:
        result = subprocess.run([
            "agentcore", "invoke", "--agent", agent_name, query_payload
        ], capture_output=True, text=True, check=True)
        
        if "access denied" in result.stdout.lower() or "permission" in result.stdout.lower():
            print("❌ Query execution test failed - missing StartQueryExecution permission")
            print(f"Response: {result.stdout}")
            return False
        else:
            print("✅ Query execution test passed")
            print(f"📋 Response preview: {result.stdout[:200]}...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Query execution test failed: {e}")
        return False
    
    # Test 3: Blockchain-specific query
    print("\n📋 Test 3: Blockchain Data Query")
    blockchain_payload = '{"prompt": "How many Bitcoin blocks were created today?"}'
    
    try:
        result = subprocess.run([
            "agentcore", "invoke", "--agent", agent_name, blockchain_payload
        ], capture_output=True, text=True, check=True)
        
        print("✅ Blockchain query test completed!")
        print(f"📋 Response: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Blockchain query test failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(
        description="Deploy Blockchain Data Processing Agent to Amazon Bedrock AgentCore"
    )
    parser.add_argument(
        "--agent-name", 
        default="blockchain-data-agent",
        help="Name for the AgentCore agent (default: blockchain-data-agent)"
    )
    parser.add_argument(
        "--skip-local-test", 
        action="store_true",
        help="Skip local testing (requires Docker/Finch/Podman)"
    )
    parser.add_argument(
        "--skip-deployment-test", 
        action="store_true",
        help="Skip testing the deployed agent"
    )
    
    args = parser.parse_args()
    
    print("🚀 Blockchain Data Processing Agent - AgentCore Deployment")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Update policy with dynamic bucket ARN
    print("\n📋 IAM Policy Update")
    print("-" * 20)
    if not update_policy_with_dynamic_bucket():
        print("❌ Failed to update IAM policy with dynamic bucket ARN")
        sys.exit(1)
    
    # Ensure IAM role exists with proper permissions
    print("\n🔐 IAM Role Setup")
    print("-" * 20)
    role_arn = ensure_iam_role_exists()
    if not role_arn:
        print("❌ IAM role setup failed.")
        sys.exit(1)
    
    # Configure agent with IAM role
    if not configure_agent(args.agent_name, role_arn):
        print("❌ Agent configuration failed.")
        sys.exit(1)
    
    # Test locally (optional)
    if not args.skip_local_test:
        print("\n🧪 Local Testing (Optional)")
        print("-" * 30)
        test_locally(args.agent_name)
    else:
        print("⏭️ Skipping local test as requested")
    
    # Deploy to AWS
    print(f"\n🚀 AWS Deployment")
    print("-" * 20)
    if not deploy_to_aws(args.agent_name):
        print("❌ Deployment failed.")
        sys.exit(1)
    
    # Test deployment
    if not args.skip_deployment_test:
        print(f"\n🔬 Deployment Testing")
        print("-" * 25)
        test_deployment(args.agent_name)
    else:
        print("⏭️ Skipping deployment test as requested")
    
    print("\n🎉 Deployment Complete!")
    print("=" * 25)
    print(f"✅ Agent '{args.agent_name}' is now running on Amazon Bedrock AgentCore")
    print("\n📋 Next Steps:")
    print(f"   • Test your agent: agentcore invoke --agent-name {args.agent_name} '{{\"prompt\": \"Your question here\"}}'")
    print("   • View logs in AWS CloudWatch")
    print("   • Monitor performance in AgentCore Console")
    print("   • Set up observability with CloudWatch Application Signals")


if __name__ == "__main__":
    main()
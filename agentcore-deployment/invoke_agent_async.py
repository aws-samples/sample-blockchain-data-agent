#!/usr/bin/env python3
import boto3
import json
import uuid
import os
import argparse
import sys
from datetime import datetime
from rich.console import Console

console = Console()

class AgentChat:
    def __init__(self, agent_name, region):
        """
        Initialize the agent chat interface.
        
        Args:
            agent_name: Name of the AgentCore agent to connect to
            region: AWS region where the agent is deployed
        """
        self.region = region
        self.agent_name = agent_name
        
        # Initialize the Bedrock AgentCore clients
        self.agent_core_client = boto3.client("bedrock-agentcore", region_name=region)
        self.control_client = boto3.client("bedrock-agentcore-control", region_name=region)
        
        # Fetch agent ARN dynamically
        self.agent_runtime_arn = self._get_agent_arn()
        
        if not self.agent_runtime_arn:
            console.print(f"[red]❌ Agent '{agent_name}' not found in region {region}[/red]")
            sys.exit(1)
        
        # Generate a unique session ID for this chat session
        self.session_id = (
            str(uuid.uuid4()).replace("-", "")[:40] + "f"
        )
        
        console.print("\n[bold cyan]Blockchain Data Agent Chat Interface[/bold cyan]")
        console.print("=" * 50)
        console.print(f"[green]Agent:[/green] {self.agent_name}")
        console.print(f"[green]Region:[/green] {self.region}")
        console.print(f"[green]ARN:[/green] {self.agent_runtime_arn}")
        console.print(f"[green]Session ID:[/green] {self.session_id}")
        console.print("=" * 50)
        console.print("[dim]Type 'quit', 'exit', or 'bye' to end the chat[/dim]")
        console.print("=" * 50)
    
    def _get_agent_arn(self):
        """
        Fetch the agent ARN dynamically using the AgentCore list API.
        
        Returns:
            str: Agent runtime ARN if found, None otherwise
        """
        try:
            console.print(f"[dim]🔍 Looking up agent '{self.agent_name}'...[/dim]")
            
            # List all agent runtimes
            response = self.control_client.list_agent_runtimes()
            
            # Find the agent by name
            for agent in response.get('agentRuntimes', []):
                if agent.get('agentRuntimeName') == self.agent_name:
                    agent_id = agent['agentRuntimeId']
                    
                    # Get full agent details to retrieve ARN
                    agent_info = self.control_client.get_agent_runtime(
                        agentRuntimeId=agent_id
                    )
                    
                    agent_arn = agent_info['agentRuntimeArn']
                    status = agent_info['status']
                    
                    console.print(f"[dim]✅ Found agent with status: {status}[/dim]")
                    
                    # Warn if agent is not ready
                    if status not in ['ACTIVE', 'READY']:
                        console.print(f"[yellow]⚠️  Warning: Agent status is '{status}', not 'ACTIVE' or 'READY'[/yellow]")
                    
                    return agent_arn
            
            # Agent not found
            console.print(f"[red]❌ Agent '{self.agent_name}' not found[/red]")
            console.print("[dim]Available agents:[/dim]")
            for agent in response.get('agentRuntimes', []):
                console.print(f"  • {agent.get('agentRuntimeName')}")
            
            return None
            
        except Exception as e:
            console.print(f"[red]❌ Error fetching agent ARN: {e}[/red]")
            return None

    def extract_text_from_response(self, response_data):
        """Extract text from the expected response format"""
        try:
            if isinstance(response_data, dict):
                # Navigate the expected structure: output.message.content[0].text
                output = response_data.get("output", {})
                message = output.get("message", {})
                content = message.get("content", [])

                if content and isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        return first_content["text"]

            return None
        except (KeyError, IndexError, TypeError):
            return None

    def stream_response(self, response):
        if "text/event-stream" in response.get("contentType", ""):
            complete_text = ""
            in_tool_call = False
            tool_buffer = ""
            
            for line in response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        json_chunk = line[6:]
                        try:
                            parsed_chunk = json.loads(json_chunk)
                            if isinstance(parsed_chunk, str):
                                text_chunk = parsed_chunk
                            else:
                                text_chunk = json.dumps(
                                    parsed_chunk, ensure_ascii=False
                                )
                                text_chunk += "\n\n"
                            
                            # Detect tool call markers
                            if "<tool_call>" in text_chunk:
                                in_tool_call = True
                                tool_buffer = ""
                                console.print("\n[bold yellow]🔧 Tool Call:[/bold yellow]", end="")
                                continue
                            elif "</tool_call>" in text_chunk:
                                in_tool_call = False
                                # Parse and format the tool call
                                self._format_tool_call(tool_buffer)
                                console.print()
                                continue
                            
                            # Buffer tool call content
                            if in_tool_call:
                                tool_buffer += text_chunk
                            else:
                                # Regular response text
                                console.print(text_chunk, end="", style="white")
                            
                            complete_text += text_chunk
                        except json.JSONDecodeError:
                            console.print(json_chunk)
                            continue
            
            console.print()
            return {}
    
    def _format_tool_call(self, tool_buffer):
        """Format and display tool call information"""
        lines = tool_buffer.strip().split('\n')
        tool_name = None
        tool_params = None
        
        for line in lines:
            if line.startswith("name:"):
                tool_name = line.split("name:", 1)[1].strip()
            elif line.startswith("params:"):
                tool_params = line.split("params:", 1)[1].strip()
        
        if tool_name:
            console.print(f"\n  [cyan]Tool:[/cyan] {tool_name}")
        if tool_params:
            try:
                # Try to pretty-print JSON params
                params_dict = eval(tool_params)
                console.print(f"  [cyan]Parameters:[/cyan]")
                for key, value in params_dict.items():
                    console.print(f"    • {key}: [dim]{value}[/dim]")
            except:
                console.print(f"  [cyan]Parameters:[/cyan] {tool_params}")

        elif response.get("contentType") == "application/json":
            # Handle standard JSON response
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode("utf-8"))

            try:
                response_data = json.loads("".join(content))
                text = self.extract_text_from_response(response_data)
                if text:
                    print(text, end="", flush=True)
                    response_text = text
            except json.JSONDecodeError:
                pass

        else:
            # For other content types, try to extract from the response object
            text = self.extract_text_from_response(response)
            if text:
                print(text, end="", flush=True)
                response_text = text

        return response_text

    def send_message(self, user_input):
        """Send a message to the agent and stream the response"""
        try:
            # Prepare the payload
            payload = json.dumps(
                {
                    "prompt": user_input
                }
            )

            # Invoke the agent
            response = self.agent_core_client.invoke_agent_runtime(
                agentRuntimeArn=self.agent_runtime_arn,
                runtimeSessionId=self.session_id,
                payload=payload,
                qualifier="DEFAULT",
            )

            # Stream the response
            return self.stream_response(response)

        except Exception as e:
            print(f"\n Error: {e}")
            return None

    def chat_loop(self):
        """Main chat loop"""
        try:
            while True:
                # Get user input
                try:
                    user_input = input("\n You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n\nGoodbye!")
                    break

                # Check for exit commands
                if user_input.lower() in ["quit", "exit", "bye", "q"]:
                    print("Goodbye!")
                    break

                # Skip empty input
                if not user_input:
                    continue

                # Send message and get response
                print("Agent: ", end="", flush=True)
                response = self.send_message(user_input)

                if response is None:
                    print("Sorry, I couldn't process your request. Please try again.")

        except KeyboardInterrupt:
            print("\n\nChat interrupted. Goodbye!")


def main():
    """Main function to start the chat interface"""
    parser = argparse.ArgumentParser(
        description="Interactive chat interface for AgentCore blockchain agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Chat with agent using default region
  python invoke_agent_async.py --agent-name blockchain_agent
  
  # Chat with agent in specific region
  python invoke_agent_async.py --agent-name blockchain_agent --region us-west-2
  
  # Use environment variables (legacy)
  export AGENT_NAME=blockchain_agent
  export AWS_REGION=us-east-1
  python invoke_agent_async.py
        """
    )
    
    parser.add_argument(
        "--agent-name",
        default=os.environ.get("AGENT_NAME"),
        help="Name of the AgentCore agent (default: from AGENT_NAME env var)"
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region (default: from AWS_REGION env var or us-east-1)"
    )
    
    args = parser.parse_args()
    
    # Validate required arguments
    if not args.agent_name:
        console.print("[red]❌ Error: --agent-name is required[/red]")
        console.print("\nUsage:")
        console.print("  python invoke_agent_async.py --agent-name blockchain_agent")
        console.print("\nOr set environment variable:")
        console.print("  export AGENT_NAME=blockchain_agent")
        sys.exit(1)
    
    # Create chat instance and start loop
    chat = AgentChat(args.agent_name, args.region)
    chat.chat_loop()


if __name__ == "__main__":
    main()

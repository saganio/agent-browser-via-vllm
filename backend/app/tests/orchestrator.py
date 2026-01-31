"""
AI Agent Orchestrator for browser test execution
"""

import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime, timezone
import aiohttp
import subprocess

from app.projects.schemas import VLLMConfig


# Browser tool definitions for the LLM
BROWSER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Navigate to a specified URL using the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element on the current page using its CSS selector or element reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector or element reference (e.g., @e1)."}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill",
            "description": "Fill a text input field with the specified text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector or element reference."},
                    "text": {"type": "string", "description": "Text to fill in the input."}
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_text",
            "description": "Get the text content of an element.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector or element reference."}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_snapshot",
            "description": "Get a snapshot of the current page state including accessible elements.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to save the screenshot."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_wait",
            "description": "Wait for an element to appear or a specified duration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to wait for."},
                    "milliseconds": {"type": "integer", "description": "Duration to wait in milliseconds."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_scroll",
            "description": "Scroll the page in a specified direction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Direction to scroll."},
                    "amount": {"type": "integer", "description": "Amount to scroll in pixels."}
                },
                "required": ["direction", "amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_url",
            "description": "Get the current page URL.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_title",
            "description": "Get the current page title.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_close",
            "description": "Close the browser.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


SYSTEM_PROMPT = """You are an expert web automation agent. Your goal is to fulfill user requests by interacting with a web browser.

You have access to browser tools that allow you to navigate, click, fill forms, take screenshots, and more.

When executing a task:
1. First, understand what the user wants to accomplish
2. Break down the task into smaller steps
3. Use browser_navigate to go to URLs
4. Use browser_snapshot to understand the current page structure
5. Use browser_click, browser_fill to interact with elements
6. Use browser_screenshot to capture results
7. Always verify your actions worked before proceeding

Be methodical and careful. If something doesn't work, try alternative approaches.
When the task is complete, summarize what you accomplished.

IMPORTANT: Always use the tools provided. Do not make up or assume page content - use browser_snapshot to see what's actually on the page."""


class BrowserToolExecutor:
    """Execute browser tools via agent-browser CLI"""
    
    COMMAND_MAP = {
        "browser_navigate": lambda args: ["open", args.get("url")],
        "browser_click": lambda args: ["click", args.get("selector")],
        "browser_fill": lambda args: ["fill", args.get("selector"), args.get("text")],
        "browser_get_text": lambda args: ["get", "text", args.get("selector")],
        "browser_snapshot": lambda args: ["snapshot", "-i"],
        "browser_screenshot": lambda args: ["screenshot", args.get("path", "screenshot.png")],
        "browser_wait": lambda args: ["wait", args.get("selector") or str(args.get("milliseconds", 1000))],
        "browser_scroll": lambda args: ["scroll", args.get("direction"), str(args.get("amount", 100))],
        "browser_get_url": lambda args: ["get", "url"],
        "browser_get_title": lambda args: ["get", "title"],
        "browser_close": lambda args: ["close"],
    }
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a browser tool"""
        
        if tool_name not in self.COMMAND_MAP:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            command_builder = self.COMMAND_MAP[tool_name]
            command_args = command_builder(arguments)
            
            # Filter out None values
            command_args = [str(arg) for arg in command_args if arg is not None]
            
            # Build full command
            full_command = ["agent-browser"] + command_args + ["--json"]
            
            # Execute asynchronously
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60.0  # 60 second timeout
            )
            
            output = stdout.decode().strip()
            error = stderr.decode().strip()
            
            if process.returncode != 0:
                return {
                    "success": False,
                    "error": error or f"Command failed with exit code {process.returncode}"
                }
            
            # Try to parse as JSON
            try:
                json_output = json.loads(output)
                return {"success": True, "data": json_output}
            except json.JSONDecodeError:
                return {"success": True, "data": output}
                
        except asyncio.TimeoutError:
            return {"success": False, "error": "Tool execution timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "agent-browser CLI not found. Please install it first."}
        except Exception as e:
            return {"success": False, "error": str(e)}


class VLLMClient:
    """Client for vLLM API"""
    
    def __init__(self, config: VLLMConfig):
        self.api_url = config.api_url
        self.model_name = config.model_name
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.api_key = config.api_key
        
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Generate a response from the LLM"""
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(
                f"{self.api_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]


class AgentOrchestrator:
    """Orchestrates the AI agent for browser automation"""
    
    def __init__(self, vllm_config: VLLMConfig):
        self.llm_client = VLLMClient(vllm_config)
        self.tool_executor = BrowserToolExecutor()
        self.conversation_history: List[Dict[str, Any]] = []
        self.max_iterations = 20  # Prevent infinite loops
    
    async def execute_command(
        self,
        command: str,
        test_run_id: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a natural language command"""
        
        # Initialize conversation
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": command}
        ]
        
        sequence = 0
        iterations = 0
        
        yield {
            "type": "status",
            "test_run_id": test_run_id,
            "sequence": sequence,
            "data": {"message": f"Starting execution: {command}"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        sequence += 1
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # Get LLM response
                response = await self.llm_client.generate(
                    messages=self.conversation_history,
                    tools=BROWSER_TOOLS
                )
                
                # Add response to history
                self.conversation_history.append(response)
                
                # Check for tool calls
                tool_calls = response.get("tool_calls", [])
                
                if tool_calls:
                    # Execute each tool call
                    for tool_call in tool_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_args_str = tool_call["function"].get("arguments", "{}")
                        
                        # Parse arguments
                        try:
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        yield {
                            "type": "tool_call",
                            "test_run_id": test_run_id,
                            "sequence": sequence,
                            "data": {
                                "tool_name": tool_name,
                                "arguments": tool_args
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        sequence += 1
                        
                        # Execute tool
                        result = await self.tool_executor.execute(tool_name, tool_args)
                        
                        yield {
                            "type": "tool_result",
                            "test_run_id": test_run_id,
                            "sequence": sequence,
                            "data": {
                                "tool_name": tool_name,
                                "result": result
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        sequence += 1
                        
                        # Added: Automatic screenshot for visualization after successful interaction
                        if result.get("success") and tool_name in ["browser_navigate", "browser_click", "browser_fill", "browser_scroll", "browser_wait"]:
                            try:
                                # Generate unique path
                                screenshot_filename = f"step_{sequence}_stream.png"
                                screenshot_args = {"path": screenshot_filename}
                                
                                # Take screenshot
                                screen_result = await self.tool_executor.execute("browser_screenshot", screenshot_args)
                                
                                if screen_result.get("success"):
                                    # Read file and encode to base64
                                    import base64
                                    import os
                                    
                                    # Get the actual path returned by the tool (it might be absolute or relative)
                                    # The CLI typically creates files in current dir if relative
                                    # We can try to read from where we expect it
                                    # But better to check what the tool returned
                                    
                                    # Assuming standard execution in current dir
                                    if os.path.exists(screenshot_filename):
                                        with open(screenshot_filename, "rb") as image_file:
                                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                                            
                                        yield {
                                            "type": "viewport_update",
                                            "test_run_id": test_run_id,
                                            "sequence": sequence,
                                            "data": {
                                                "image": f"data:image/png;base64,{encoded_string}"
                                            },
                                            "timestamp": datetime.now(timezone.utc).isoformat()
                                        }
                                        # Cleanup temp file
                                        os.remove(screenshot_filename)
                            except Exception as e:
                                # Don't fail the whole step if streaming fails
                                print(f"Failed to capture streaming screenshot: {e}")

                        # Add tool result to conversation
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "content": json.dumps(result)
                        })
                
                else:
                    # No tool calls - LLM is providing a response
                    content = response.get("content", "")
                    
                    yield {
                        "type": "llm_response",
                        "test_run_id": test_run_id,
                        "sequence": sequence,
                        "data": {"content": content},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    sequence += 1
                    
                    # Check if task seems complete
                    if self._is_task_complete(content):
                        yield {
                            "type": "complete",
                            "test_run_id": test_run_id,
                            "sequence": sequence,
                            "data": {"message": "Task completed successfully"},
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        return
                    
                    # If not complete and no tool calls, we might be stuck
                    # Add a prompt to continue
                    self.conversation_history.append({
                        "role": "user",
                        "content": "Please continue with the task. Use the browser tools to interact with the page."
                    })
                    
            except aiohttp.ClientError as e:
                yield {
                    "type": "error",
                    "test_run_id": test_run_id,
                    "sequence": sequence,
                    "data": {"error": f"LLM API error: {str(e)}"},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                return
                
            except Exception as e:
                yield {
                    "type": "error",
                    "test_run_id": test_run_id,
                    "sequence": sequence,
                    "data": {"error": str(e)},
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                return
        
        # Max iterations reached
        yield {
            "type": "error",
            "test_run_id": test_run_id,
            "sequence": sequence,
            "data": {"error": f"Max iterations ({self.max_iterations}) reached"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _is_task_complete(self, content: str) -> bool:
        """Check if the LLM response indicates task completion"""
        completion_indicators = [
            "task is complete",
            "successfully completed",
            "finished the task",
            "task has been completed",
            "i have completed",
            "the task is done",
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in completion_indicators)

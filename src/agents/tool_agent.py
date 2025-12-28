"""
Tool Agent - The Tool Guild.

Responsible for:
- Executing actions via tools
- Interfacing with APIs, code, OS
- Sandboxed execution
"""

import json
from typing import Any

import structlog

from src.agents.base import AgentConstraints, AgentState, AgentType, BaseAgent
from src.core.message import (
    AgentMessage,
    AgentResult,
    Reflection,
    Task,
    utc_now,
)
from src.providers.base import LLMProvider, ToolDefinition
from src.tools.registry import ToolRegistry, get_tool_registry

logger = structlog.get_logger()


TOOL_AGENT_SYSTEM_PROMPT = """You are a Tool Agent in the Agent Village.

Your role is to execute tasks by using available tools effectively.

When given a task:
1. Understand what needs to be accomplished
2. Identify which tools are needed
3. Plan the sequence of tool calls
4. Execute tools and handle results
5. Combine results into a coherent output

Guidelines:
- Use the minimum number of tool calls needed
- Handle errors gracefully and retry if appropriate
- Validate tool outputs before proceeding
- Report progress and issues clearly

IMPORTANT - File Path Rules:
- All file operations use paths RELATIVE to the workspace root
- Do NOT include 'workspace/' prefix in paths
- Examples: 'myfile.txt', 'project/script.py', 'output/report.md'

IMPORTANT - Code Generation Rules:
- When writing Python scripts that save files, use RELATIVE paths from the script's directory
- Use 'output.txt' not 'workspace/folder/output.txt'
- If using a directory, create it first with create_directory
- After writing code, execute it to verify it works

You have access to various tools. Use them wisely to accomplish tasks efficiently."""


class ToolAgent(BaseAgent):
    """
    Tool Agent for executing actions via tools.

    Part of the Tool Guild that interfaces with external systems.
    """

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry | None = None,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
    ):
        if constraints is None:
            constraints = AgentConstraints(
                max_tokens_per_request=4096,
                can_spawn_agents=False,
                can_access_memory=True,
                risk_tolerance="medium",
                allowed_tools={"echo", "calculate", "read_file", "write_file", "web_request"},
            )

        super().__init__(
            agent_type=AgentType.TOOL,
            provider=provider,
            name=name or "tool_agent",
            constraints=constraints,
        )

        self.tool_registry = tool_registry or get_tool_registry()
        self._system_prompt = TOOL_AGENT_SYSTEM_PROMPT
        self._max_tool_iterations = 10

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Execute a task using available tools."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided",
                )

            # Get available tools for this agent
            available_tools = self.tool_registry.get_tools_for_agent(
                self.agent_type.value, self.id
            )

            if not available_tools:
                self.logger.warning("No tools available for agent")

            # Convert tools to LLM format
            tool_definitions = [
                ToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.to_json_schema()["parameters"],
                )
                for tool in available_tools
            ]

            # Execute with tool loop
            result = await self._execute_with_tools(task, message.content, tool_definitions)

            execution_time = time.time() - start_time
            self.metrics.tasks_completed += 1
            self.metrics.total_execution_time += execution_time
            self.state = AgentState.IDLE

            return result

        except Exception as e:
            self.logger.error("Tool execution failed", error=str(e))
            self.metrics.tasks_failed += 1
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _execute_with_tools(
        self,
        task: Task,
        context: dict[str, Any],
        tool_definitions: list[ToolDefinition],
    ) -> AgentResult:
        """Execute task with tool calling loop."""
        from src.providers.base import Message, MessageRole

        # Build initial prompt
        prompt = self._build_task_prompt(task, context)

        # Initialize conversation
        messages = [
            Message(role=MessageRole.SYSTEM, content=self._system_prompt),
            Message(role=MessageRole.USER, content=prompt),
        ]

        iterations = 0
        total_tokens = 0
        tool_results = []

        while iterations < self._max_tool_iterations:
            iterations += 1

            # Call LLM with tools
            completion = await self.provider.complete(
                messages,
                tools=tool_definitions if tool_definitions else None,
                tool_choice="auto" if tool_definitions else None,
                temperature=0.3,
                max_tokens=self.constraints.max_tokens_per_request,
            )

            total_tokens += completion.total_tokens

            if completion.has_tool_calls:
                # Execute tool calls
                tool_messages = []

                for tool_call in completion.tool_calls:
                    self.logger.debug(
                        "Executing tool",
                        tool=tool_call.name,
                        args=tool_call.arguments,
                    )

                    result = await self.tool_registry.execute_tool(
                        tool_call.name,
                        self.agent_type.value,
                        **tool_call.arguments,
                    )

                    tool_results.append({
                        "tool": tool_call.name,
                        "args": tool_call.arguments,
                        "result": result.to_dict(),
                    })

                    # Add tool result to conversation
                    tool_messages.append(
                        Message(
                            role=MessageRole.TOOL,
                            content=json.dumps(result.to_dict()),
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )

                # Add assistant's tool call and results to messages
                messages.append(
                    Message(
                        role=MessageRole.ASSISTANT,
                        content=completion.content,
                        tool_calls=completion.tool_calls,
                    )
                )
                messages.extend(tool_messages)

            else:
                # No tool calls - final response
                return self._create_result(
                    task_id=task.id,
                    success=True,
                    result={
                        "response": completion.content,
                        "tool_executions": tool_results,
                    },
                    confidence=0.8,
                    quality_score=0.8,
                    tokens_used=total_tokens,
                    execution_time=0,  # Will be set by caller
                )

        # Max iterations reached
        return self._create_result(
            task_id=task.id,
            success=False,
            result={"tool_executions": tool_results},
            error=f"Max tool iterations ({self._max_tool_iterations}) reached",
            tokens_used=total_tokens,
        )

    def _build_task_prompt(self, task: Task, context: dict[str, Any]) -> str:
        """Build the task prompt."""
        prompt_parts = [
            f"# Task\n{task.description}",
        ]

        if task.objective:
            prompt_parts.append(f"\n## Objective\n{task.objective}")

        if task.expected_output:
            prompt_parts.append(f"\n## Expected Output\n{task.expected_output}")

        if context:
            prompt_parts.append(f"\n## Context\n{json.dumps(context, indent=2)}")

        prompt_parts.append(
            "\n## Instructions\n"
            "Use the available tools to accomplish this task. "
            "When complete, provide a clear summary of what was accomplished."
        )

        return "\n".join(prompt_parts)

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on tool execution."""
        if not result.success:
            return Reflection(
                agent_id=self.id,
                task_id=result.task_id,
                performance_score=0.3,
                failures=[result.error or "Tool execution failed"],
            )

        result_data = result.result or {}
        tool_executions = result_data.get("tool_executions", [])
        successful_tools = sum(1 for t in tool_executions if t.get("result", {}).get("success"))

        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=result.quality_score,
            lessons_learned=[
                f"Used {len(tool_executions)} tool calls, {successful_tools} successful",
            ],
            successes=["Task completed with tools"] if result.success else [],
            recommendations=[
                "Consider caching repeated tool calls",
                "Validate tool inputs before execution",
            ],
        )

    async def can_handle(self, task: Task) -> float:
        """Assess ability to handle task."""
        description_lower = task.description.lower()

        # High confidence for action-oriented tasks
        action_keywords = [
            "execute", "run", "call", "fetch", "get", "post",
            "read", "write", "create", "delete", "update",
            "api", "request", "command", "script",
        ]

        matches = sum(1 for kw in action_keywords if kw in description_lower)
        if matches >= 2:
            return 0.9
        elif matches == 1:
            return 0.7

        return 0.5

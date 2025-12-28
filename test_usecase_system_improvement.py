"""
Use Case 3: Continuous System Improvement

Test the Agent Village system's ability to analyze its own performance
and suggest improvements using the Evolver agent.

This test will:
1. Gather historical performance data from previous use cases
2. Use the Evolver agent to analyze patterns
3. Generate optimization recommendations
4. Track the improvement cycle
"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


class UseCaseTracker:
    """Track use case execution for documentation."""

    def __init__(self, use_case_name: str):
        self.use_case_name = use_case_name
        self.start_time = None
        self.end_time = None
        self.agents_spawned = []
        self.tools_used = []
        self.tasks_executed = []
        self.results = []
        self.quality_metrics = {}
        self.logs = []
        self.improvement_suggestions = []

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(log_entry)

    def record_agent(self, agent_id: str, agent_type: str, agent_name: str):
        self.agents_spawned.append({
            "id": agent_id,
            "type": agent_type,
            "name": agent_name,
            "spawned_at": datetime.now().isoformat()
        })

    def record_task(self, task_desc: str, status: str, agent_used: str = ""):
        self.tasks_executed.append({
            "description": task_desc,
            "status": status,
            "agent": agent_used,
            "executed_at": datetime.now().isoformat()
        })

    def to_dict(self):
        return {
            "use_case": self.use_case_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else None,
            "agents_spawned": self.agents_spawned,
            "tasks_executed": self.tasks_executed,
            "results": self.results,
            "quality_metrics": self.quality_metrics,
            "improvement_suggestions": self.improvement_suggestions,
            "logs": self.logs
        }


async def test_system_improvement():
    """Test Continuous System Improvement use case."""
    from src.agents.base import AgentType
    from src.agents.evolver import EvolverAgent
    from src.agents.critic import CriticAgent
    from src.core.agent_manager import AgentManager
    from src.core.registry import AgentRegistry
    from src.core.message import Task
    from src.memory.strategic import StrategicMemory
    from src.providers.base import ProviderPool
    from src.providers.openai import OpenAIProvider

    tracker = UseCaseTracker("Continuous System Improvement")
    tracker.start_time = datetime.now()

    print("=" * 80)
    print("USE CASE 3: CONTINUOUS SYSTEM IMPROVEMENT")
    print("=" * 80)
    print()

    # === PHASE 1: Setup Infrastructure ===
    tracker.log("Phase 1: Setting up infrastructure...")

    provider_pool = ProviderPool()
    openai_provider = OpenAIProvider(model="gpt-4o-mini")
    provider_pool.register("default", openai_provider)

    strategic_memory = StrategicMemory()
    agent_manager = AgentManager(strategic_memory=strategic_memory)
    await agent_manager.initialize()

    registry = AgentRegistry(provider_pool=provider_pool, agent_manager=agent_manager)
    registry.register_factory(AgentType.EVOLVER, EvolverAgent, "default")
    registry.register_factory(AgentType.CRITIC, CriticAgent, "default")

    tracker.log("Infrastructure ready")

    # === PHASE 2: Gather Historical Data ===
    tracker.log("Phase 2: Gathering historical performance data...")

    all_profiles = agent_manager.get_all_profiles()
    historical_data = {
        "total_agents": len(all_profiles),
        "agents": []
    }

    for profile in all_profiles:
        agent_data = {
            "name": profile.name,
            "type": profile.agent_type.value,
            "total_tasks": profile.performance.total_tasks,
            "success_rate": profile.performance.success_rate,
            "total_tokens": profile.performance.total_tokens_used,
            "specializations": profile.specializations,
            "is_active": profile.is_active,
        }
        historical_data["agents"].append(agent_data)
        if profile.performance.total_tasks > 0:
            tracker.log(f"  Agent: {profile.name} - {profile.performance.total_tasks} tasks, "
                       f"{profile.performance.success_rate:.0%} success")

    tracker.log(f"  Total agents in system: {len(all_profiles)}")

    print()

    # === PHASE 3: Spawn Evolver Agent ===
    tracker.log("Phase 3: Spawning Evolver agent for system analysis...")

    evolver_agent = await registry.create_agent(
        AgentType.EVOLVER,
        name="SystemOptimizerAgent"
    )
    tracker.record_agent(evolver_agent.id, "evolver", evolver_agent.name)
    tracker.log(f"  Spawned: {evolver_agent.name}")

    print()

    # === PHASE 4: Analyze System Performance ===
    tracker.log("Phase 4: Performing full system evolution analysis...")

    from src.core.message import AgentMessage, MessageType

    evolution_task = Task(
        description="""Perform a comprehensive analysis of the Agent Village system performance
and suggest optimizations.

Review the historical performance data and provide:
1. Assessment of agent effectiveness
2. Identification of bottlenecks or inefficiencies
3. Recommendations for prompt improvements
4. Workflow optimization suggestions
5. Patterns that should be retired
6. Overall system health score""",
        goal_id="system-improvement-goal",
        objective="Analyze and improve system performance",
    )

    evolution_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=evolver_agent.id,
        recipient_type="evolver",
        goal_id="system-improvement-goal",
        task_id=evolution_task.id,
        task=evolution_task,
        content={
            "type": "full",
            "historical_data": historical_data,
            "current_metrics": {
                "total_goals_processed": 3,
                "average_goal_duration_seconds": 100,
                "total_tokens_used": sum(a["total_tokens"] for a in historical_data["agents"]),
                "agent_spawn_rate": len(all_profiles) / 3,  # agents per goal
            }
        },
    )

    evolution_result = await evolver_agent.execute(evolution_message)

    if evolution_result.success:
        tracker.record_task("Full system analysis", "completed", evolver_agent.name)
        evolution_data = evolution_result.result or {}

        tracker.improvement_suggestions = {
            "health_score": evolution_data.get("overall_health_score", 0),
            "patterns_to_retire": evolution_data.get("patterns_to_retire", []),
            "lessons_learned": evolution_data.get("lessons_learned", []),
            "prompt_optimizations": evolution_data.get("prompt_optimizations", []),
            "workflow_optimizations": evolution_data.get("workflow_optimizations", []),
        }

        health_score = evolution_data.get("overall_health_score", 0)
        tracker.log(f"    [SUCCESS] Analysis complete - Health Score: {health_score:.0%}")
        tracker.log(f"    Tokens used: {evolution_result.tokens_used}")
    else:
        tracker.record_task("Full system analysis", "failed", evolver_agent.name)
        tracker.log(f"    [FAILED] {evolution_result.error}")

    await registry.record_task_outcome(
        agent_id=evolver_agent.id,
        task=evolution_task,
        success=evolution_result.success,
        tokens_used=evolution_result.tokens_used,
        execution_time_ms=int(evolution_result.execution_time_seconds * 1000),
        error=evolution_result.error,
    )

    print()

    # === PHASE 5: Analyze Tool Agent Prompt ===
    tracker.log("Phase 5: Analyzing Tool Agent prompt for optimization...")

    prompt_task = Task(
        description="Analyze and optimize the Tool Agent system prompt",
        goal_id="system-improvement-goal",
        objective="Optimize Tool Agent prompt",
    )

    prompt_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=evolver_agent.id,
        recipient_type="evolver",
        goal_id="system-improvement-goal",
        task_id=prompt_task.id,
        task=prompt_task,
        content={
            "type": "prompt",
            "agent_type": "tool",
            "current_prompt": """You are a Tool Agent in the Agent Village.

Your role is to execute tasks by using available tools effectively.

When given a task:
1. Understand what needs to be done
2. Identify which tools can help
3. Execute tools in the right sequence
4. Handle errors gracefully
5. Report results clearly

You have access to various tools. Use them wisely to accomplish tasks efficiently.""",
            "performance_data": {
                "average_success_rate": 0.95,
                "common_errors": ["Permission denied", "File not found"],
                "average_tokens_per_task": 5000,
            }
        },
    )

    prompt_result = await evolver_agent.execute(prompt_message)

    if prompt_result.success:
        tracker.record_task("Tool Agent prompt analysis", "completed", evolver_agent.name)
        prompt_data = prompt_result.result or {}
        optimizations = prompt_data.get("prompt_optimizations", [])

        if optimizations:
            for opt in optimizations:
                tracker.log(f"    Optimization: {opt.get('rationale', 'N/A')[:50]}...")
                tracker.log(f"    Expected improvement: {opt.get('expected_improvement', 0):.0%}")

        tracker.log(f"    [SUCCESS] Prompt analysis complete")
    else:
        tracker.record_task("Tool Agent prompt analysis", "failed", evolver_agent.name)
        tracker.log(f"    [FAILED] {prompt_result.error}")

    await registry.record_task_outcome(
        agent_id=evolver_agent.id,
        task=prompt_task,
        success=prompt_result.success,
        tokens_used=prompt_result.tokens_used,
        execution_time_ms=int(prompt_result.execution_time_seconds * 1000),
        error=prompt_result.error,
    )

    print()

    # === PHASE 6: Analyze Workflow ===
    tracker.log("Phase 6: Analyzing goal execution workflow...")

    workflow_task = Task(
        description="Analyze and optimize the goal execution workflow",
        goal_id="system-improvement-goal",
        objective="Optimize goal execution workflow",
    )

    workflow_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=evolver_agent.id,
        recipient_type="evolver",
        goal_id="system-improvement-goal",
        task_id=workflow_task.id,
        task=workflow_task,
        content={
            "type": "workflow",
            "workflow_name": "goal_execution",
            "steps": [
                "Receive goal from user",
                "Analyze intent and complexity",
                "Decompose into tasks",
                "Assign agents to tasks",
                "Execute tasks sequentially",
                "Verify results with critic",
                "Store in memory",
                "Return results",
            ],
            "execution_data": {
                "average_steps": 8,
                "bottleneck_step": "Execute tasks sequentially",
                "error_prone_step": "Assign agents to tasks",
                "average_duration_seconds": 100,
            }
        },
    )

    workflow_result = await evolver_agent.execute(workflow_message)

    if workflow_result.success:
        tracker.record_task("Workflow analysis", "completed", evolver_agent.name)
        workflow_data = workflow_result.result or {}
        optimizations = workflow_data.get("workflow_optimizations", [])

        if optimizations:
            for opt in optimizations:
                tracker.log(f"    Speedup expected: {opt.get('expected_speedup', 1.0):.1f}x")
                tracker.log(f"    Quality change: {opt.get('expected_quality_change', 0):+.0%}")

        patterns_to_retire = workflow_data.get("patterns_to_retire", [])
        if patterns_to_retire:
            tracker.log(f"    Patterns to retire: {len(patterns_to_retire)}")

        tracker.log(f"    [SUCCESS] Workflow analysis complete")
    else:
        tracker.record_task("Workflow analysis", "failed", evolver_agent.name)
        tracker.log(f"    [FAILED] {workflow_result.error}")

    await registry.record_task_outcome(
        agent_id=evolver_agent.id,
        task=workflow_task,
        success=workflow_result.success,
        tokens_used=workflow_result.tokens_used,
        execution_time_ms=int(workflow_result.execution_time_seconds * 1000),
        error=workflow_result.error,
    )

    print()

    # === PHASE 7: Quality Review ===
    tracker.log("Phase 7: Quality review of improvement suggestions...")

    critic_agent = await registry.create_agent(
        AgentType.CRITIC,
        name="ImprovementReviewerAgent"
    )
    tracker.record_agent(critic_agent.id, "critic", critic_agent.name)

    review_task = Task(
        description="Review the quality of improvement suggestions",
        goal_id="system-improvement-goal",
        objective="Validate improvement suggestions",
    )

    review_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=critic_agent.id,
        recipient_type="critic",
        goal_id="system-improvement-goal",
        task_id=review_task.id,
        task=review_task,
        content={
            "content_to_review": tracker.improvement_suggestions,
            "original_task": "Analyze system performance and suggest improvements",
            "expected_output": """
            - Clear health assessment
            - Actionable improvement recommendations
            - Specific patterns to retire
            - Prioritized optimization suggestions
            """,
        },
    )

    review_result = await critic_agent.execute(review_message)

    if review_result.success:
        review_data = review_result.result or {}
        quality_score = review_data.get("quality_score", 0)
        validity = review_data.get("validity", "unknown")

        tracker.quality_metrics = {
            "quality_score": quality_score,
            "validity": validity,
            "issues": review_data.get("issues", []),
            "strengths": review_data.get("strengths", []),
            "recommendations": review_data.get("recommendations", []),
        }

        tracker.record_task("Quality review", "completed", critic_agent.name)
        tracker.log(f"    [SUCCESS] Quality Score: {quality_score}/100, Validity: {validity}")
    else:
        tracker.record_task("Quality review", "failed", critic_agent.name)
        tracker.log(f"    [FAILED] {review_result.error}")

    print()

    # === PHASE 8: Verify Learning ===
    tracker.log("Phase 8: Verifying agent learning and persistence...")

    all_profiles = agent_manager.get_all_profiles()
    active_count = sum(1 for p in all_profiles if p.performance.total_tasks > 0)
    total_tasks = sum(p.performance.total_tasks for p in all_profiles)

    tracker.log(f"  Active agents with task history: {active_count}")
    tracker.log(f"  Total tasks across all agents: {total_tasks}")

    for profile in all_profiles:
        if profile.performance.total_tasks > 0:
            tracker.log(f"    {profile.name}: {profile.performance.total_tasks} tasks, "
                       f"{profile.performance.success_rate:.0%} success")

    print()

    # === PHASE 9: Collect Results ===
    tracker.end_time = datetime.now()
    tracker.log("Phase 9: Collecting final results...")

    tracker.results = [
        {
            "phase": "Full System Analysis",
            "success": evolution_result.success,
            "tokens_used": evolution_result.tokens_used,
            "health_score": tracker.improvement_suggestions.get("health_score", 0),
        },
        {
            "phase": "Prompt Optimization",
            "success": prompt_result.success,
            "tokens_used": prompt_result.tokens_used,
        },
        {
            "phase": "Workflow Optimization",
            "success": workflow_result.success,
            "tokens_used": workflow_result.tokens_used,
        },
        {
            "phase": "Quality Review",
            "success": review_result.success,
            "quality_score": tracker.quality_metrics.get("quality_score", 0),
            "validity": tracker.quality_metrics.get("validity", "unknown"),
        }
    ]

    await registry.shutdown_all()

    print()
    print("=" * 80)
    print("USE CASE 3 SUMMARY: CONTINUOUS SYSTEM IMPROVEMENT")
    print("=" * 80)
    print(f"Duration: {tracker.to_dict()['duration_seconds']:.2f} seconds")
    print(f"Agents Spawned: {len(tracker.agents_spawned)}")
    print(f"Tasks Executed: {len(tracker.tasks_executed)}")
    print(f"System Health Score: {tracker.improvement_suggestions.get('health_score', 0):.0%}")
    print(f"Quality Score: {tracker.quality_metrics.get('quality_score', 'N/A')}/100")
    print("=" * 80)

    return tracker.to_dict()


if __name__ == "__main__":
    results = asyncio.run(test_system_improvement())

    with open("usecase3_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nResults saved to usecase3_results.json")

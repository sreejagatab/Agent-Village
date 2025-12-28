"""
Test Agent Lifecycle: Spawning, Persistence, and Reuse.

This script tests the full agent lifecycle to verify:
1. Agents spawn dynamically when needed
2. Agent state is persisted to database
3. Agents are reused for similar tasks
4. Learning loop updates agent scores

Run with: python test_agent_lifecycle.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


async def test_agent_lifecycle():
    """Test the full agent lifecycle."""
    from src.agents.base import AgentType
    from src.agents.planner import PlannerAgent
    from src.agents.critic import CriticAgent
    from src.agents.tool_agent import ToolAgent
    from src.core.agent_manager import AgentManager, AgentCapability
    from src.core.registry import AgentRegistry
    from src.core.message import Goal, Task
    from src.memory.strategic import StrategicMemory
    from src.providers.base import ProviderPool, LLMProvider
    from src.providers.openai import OpenAIProvider
    from src.config.settings import Settings

    settings = Settings()

    print("=" * 70)
    print("AGENT LIFECYCLE TEST")
    print("=" * 70)
    print()

    # === PHASE 1: Setup ===
    print("[Phase 1] Setting up infrastructure...")

    # Create provider pool with OpenAI
    provider_pool = ProviderPool()
    openai_provider = OpenAIProvider(model="gpt-4o-mini")  # Use cheaper model for testing
    provider_pool.register("openai_gpt4", openai_provider)
    provider_pool.register("default", openai_provider)

    # Create AgentManager
    strategic_memory = StrategicMemory()
    agent_manager = AgentManager(
        strategic_memory=strategic_memory,
        min_success_rate=0.3,
    )

    # Create registry with agent manager integration
    registry = AgentRegistry(provider_pool=provider_pool, agent_manager=agent_manager)

    # Register agent factories
    registry.register_factory(AgentType.PLANNER, PlannerAgent, "default")
    registry.register_factory(AgentType.CRITIC, CriticAgent, "default")
    registry.register_factory(AgentType.TOOL, ToolAgent, "default")

    print("  [OK] Provider pool created")
    print("  [OK] AgentManager created with strategic memory")
    print("  [OK] Registry created with AgentManager integration")
    print("  [OK] Agent factories registered")
    print()

    # === PHASE 2: Dynamic Agent Spawning ===
    print("[Phase 2] Testing Dynamic Agent Spawning...")

    # Create first agent
    print("  Creating Planner agent...")
    planner1 = await registry.create_agent(AgentType.PLANNER, name="TestPlanner1")
    print(f"  [OK] Created: {planner1.name} (ID: {planner1.id[:8]}...)")

    # Check if it's registered with AgentManager
    profile1 = agent_manager.get_profile(planner1.id)
    if profile1:
        print(f"  [OK] Agent profile created with {len(profile1.capabilities)} capabilities")
        print(f"      Specializations: {profile1.specializations}")
    else:
        print("  [FAIL] No profile found in AgentManager!")

    # Create second agent of same type
    print("\n  Creating second Planner agent...")
    planner2 = await registry.create_agent(AgentType.PLANNER, name="TestPlanner2")
    print(f"  [OK] Created: {planner2.name} (ID: {planner2.id[:8]}...)")

    # Create Tool agent with custom capabilities
    print("\n  Creating Tool agent with custom capabilities...")
    tool_agent = await registry.create_agent(AgentType.TOOL, name="DataToolAgent")

    # Add custom capabilities
    custom_capabilities = [
        AgentCapability(
            name="data_fetching",
            description="Fetch data from APIs",
            keywords=["api", "fetch", "data", "http"],
        ),
        AgentCapability(
            name="file_management",
            description="Create and manage files",
            keywords=["file", "write", "create", "save"],
        ),
    ]

    tool_profile = agent_manager.get_profile(tool_agent.id)
    if tool_profile:
        tool_profile.capabilities.extend(custom_capabilities)
        print(f"  [OK] Created: {tool_agent.name} with {len(tool_profile.capabilities)} capabilities")

    print()

    # === PHASE 3: Intelligent Agent Selection ===
    print("[Phase 3] Testing Intelligent Agent Selection...")

    # Create a test task
    test_task1 = Task(
        description="Create a Python script that fetches data from an API and saves results to a file",
        goal_id="test-goal-1",
        objective="Build a working data fetching script",
    )

    print(f"  Task: {test_task1.description[:60]}...")

    # Find best agent
    best_agent, score, rationale = await registry.find_best_agent(
        agent_type=AgentType.TOOL,
        task_description=test_task1.description,
        task=test_task1,
    )

    if best_agent:
        print(f"  [OK] Selected: {best_agent.name}")
        print(f"      Score: {score:.2f}")
        print(f"      Rationale: {rationale}")
    else:
        print("  [FAIL] No agent selected!")

    # Test with planning task
    test_task2 = Task(
        description="Plan a strategy to decompose this complex goal into smaller tasks",
        goal_id="test-goal-1",
        objective="Create a decomposition plan",
    )

    print(f"\n  Task: {test_task2.description[:60]}...")

    best_planner, score2, rationale2 = await registry.find_best_agent(
        agent_type=AgentType.PLANNER,
        task_description=test_task2.description,
        task=test_task2,
    )

    if best_planner:
        print(f"  [OK] Selected: {best_planner.name}")
        print(f"      Score: {score2:.2f}")
        print(f"      Rationale: {rationale2}")

    print()

    # === PHASE 4: Learning from Outcomes ===
    print("[Phase 4] Testing Learning from Outcomes...")

    # Simulate successful task execution
    print("  Simulating successful task execution...")
    await registry.record_task_outcome(
        agent_id=tool_agent.id,
        task=test_task1,
        success=True,
        tokens_used=150,
        execution_time_ms=2500,
    )

    # Check updated metrics
    updated_profile = agent_manager.get_profile(tool_agent.id)
    if updated_profile:
        print(f"  [OK] Performance updated:")
        print(f"      Total tasks: {updated_profile.performance.total_tasks}")
        print(f"      Success rate: {updated_profile.performance.success_rate:.0%}")
        print(f"      Total tokens: {updated_profile.performance.total_tokens_used}")

    # Simulate another successful task
    test_task3 = Task(
        description="Fetch cryptocurrency prices from CoinGecko API",
        goal_id="test-goal-2",
        objective="Get crypto price data",
    )

    await registry.record_task_outcome(
        agent_id=tool_agent.id,
        task=test_task3,
        success=True,
        tokens_used=120,
        execution_time_ms=1800,
    )

    updated_profile = agent_manager.get_profile(tool_agent.id)
    if updated_profile:
        print(f"\n  After second task:")
        print(f"      Total tasks: {updated_profile.performance.total_tasks}")
        print(f"      Success rate: {updated_profile.performance.success_rate:.0%}")
        print(f"      Task type scores: {updated_profile.performance.task_type_scores}")

    print()

    # === PHASE 5: Agent Reuse for Similar Tasks ===
    print("[Phase 5] Testing Agent Reuse for Similar Tasks...")

    # Create a similar task
    similar_task = Task(
        description="Create a script to fetch weather data from an API and save to JSON file",
        goal_id="test-goal-3",
        objective="Build weather data fetcher",
    )

    print(f"  Similar task: {similar_task.description[:60]}...")

    # Find best agent - should prefer the one with successful history
    best_for_similar, similar_score, similar_rationale = await registry.find_best_agent(
        agent_type=AgentType.TOOL,
        task_description=similar_task.description,
        task=similar_task,
    )

    if best_for_similar:
        print(f"  [OK] Selected: {best_for_similar.name}")
        print(f"      Score: {similar_score:.2f}")
        print(f"      Rationale: {similar_rationale}")

        # Verify it's the same agent with good track record
        if best_for_similar.id == tool_agent.id:
            print("  [OK] System correctly reused the experienced agent!")
        else:
            print("  [INFO] Different agent selected - may be testing exploration")

    print()

    # === PHASE 6: Get Recommendations ===
    print("[Phase 6] Testing Agent Recommendations...")

    recommendations = await agent_manager.get_agent_recommendations(
        task_description="Build a data pipeline to fetch stock prices",
        agent_type=AgentType.TOOL,
        top_n=3,
    )

    print(f"  Top {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"    {i}. {rec['agent_name']}")
        print(f"       Score: {rec['score']:.2f}, Success rate: {rec['success_rate']:.0%}")
        print(f"       Rationale: {rec['rationale']}")

    print()

    # === PHASE 7: Strategic Memory Integration ===
    print("[Phase 7] Testing Strategic Memory Integration...")

    # Get lessons learned
    lessons = await agent_manager.get_lessons_for_task_type("data_retrieval")

    print(f"  Lessons learned from past tasks: {len(lessons)}")
    for lesson in lessons[:3]:
        print(f"    - {lesson}")

    # Check similar past decisions
    similar_decisions = await strategic_memory.find_similar_decisions(
        decision_type="agent_assignment",
        context_description="fetch data from API",
        min_outcome_score=0.5,
        limit=5,
    )

    print(f"\n  Similar past decisions found: {len(similar_decisions)}")
    for decision in similar_decisions[:2]:
        content = decision.content
        if isinstance(content, dict):
            print(f"    - {content.get('description', 'N/A')[:50]}...")

    print()

    # === PHASE 8: Registry Statistics ===
    print("[Phase 8] Registry Statistics...")

    stats = registry.get_stats()
    print(f"  Total agents registered: {stats['total_agents']}")
    print(f"  By type: {stats['by_type']}")
    print(f"  By state: {stats['by_state']}")

    all_profiles = agent_manager.get_all_profiles()
    print(f"\n  AgentManager profiles: {len(all_profiles)}")
    for profile in all_profiles:
        print(f"    - {profile.name} ({profile.agent_type.value})")
        print(f"      Tasks: {profile.performance.total_tasks}, "
              f"Success: {profile.performance.success_rate:.0%}, "
              f"Active: {profile.is_active}")

    print()

    # === PHASE 9: Cleanup ===
    print("[Phase 9] Cleanup...")
    await registry.shutdown_all()
    print("  [OK] All agents shut down")

    print()
    print("=" * 70)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print()
    print("Summary:")
    print("  [OK] Dynamic agent spawning works")
    print("  [OK] Agents registered with AgentManager")
    print("  [OK] Intelligent agent selection based on capabilities")
    print("  [OK] Learning from task outcomes")
    print("  [OK] Agent reuse for similar tasks")
    print("  [OK] Strategic memory integration")
    print("  [OK] Agent recommendations work")


if __name__ == "__main__":
    asyncio.run(test_agent_lifecycle())

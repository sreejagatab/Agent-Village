"""
Use Case 1: Market Research Automation

Test the Agent Village system with a real-world market research task:
"Research and analyze the top cryptocurrency projects with price data and market analysis"

This test will:
1. Submit a complex goal requiring multiple capabilities
2. Track agent spawning and selection
3. Monitor tool usage and execution
4. Evaluate quality of generated output
5. Save detailed results for documentation
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add src to path
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

    def record_tool(self, tool_name: str, success: bool, result_preview: str = ""):
        self.tools_used.append({
            "tool": tool_name,
            "success": success,
            "result_preview": result_preview[:200] if result_preview else "",
            "executed_at": datetime.now().isoformat()
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
            "tools_used": self.tools_used,
            "tasks_executed": self.tasks_executed,
            "results": self.results,
            "quality_metrics": self.quality_metrics,
            "logs": self.logs
        }


async def test_market_research():
    """Test Market Research Automation use case."""
    from src.agents.base import AgentType
    from src.agents.planner import PlannerAgent
    from src.agents.critic import CriticAgent
    from src.agents.tool_agent import ToolAgent
    from src.core.agent_manager import AgentManager
    from src.core.registry import AgentRegistry
    from src.core.message import Goal, Task
    from src.memory.strategic import StrategicMemory
    from src.providers.base import ProviderPool
    from src.providers.openai import OpenAIProvider
    from src.tools.registry import get_tool_registry
    from src.tools.file import create_file_tools
    from src.tools.web import create_web_tools

    tracker = UseCaseTracker("Market Research Automation")
    tracker.start_time = datetime.now()

    print("=" * 80)
    print("USE CASE 1: MARKET RESEARCH AUTOMATION")
    print("=" * 80)
    print()

    # === PHASE 1: Setup Infrastructure ===
    tracker.log("Phase 1: Setting up infrastructure...")

    # Create provider pool
    provider_pool = ProviderPool()
    openai_provider = OpenAIProvider(model="gpt-4o-mini")
    provider_pool.register("default", openai_provider)

    # Create AgentManager with strategic memory
    strategic_memory = StrategicMemory()
    agent_manager = AgentManager(strategic_memory=strategic_memory)
    await agent_manager.initialize()

    # Create registry
    registry = AgentRegistry(provider_pool=provider_pool, agent_manager=agent_manager)

    # Register agent factories
    registry.register_factory(AgentType.PLANNER, PlannerAgent, "default")
    registry.register_factory(AgentType.CRITIC, CriticAgent, "default")
    registry.register_factory(AgentType.TOOL, ToolAgent, "default")

    # Register tools
    tool_registry = get_tool_registry()
    for tool in create_file_tools():
        tool_registry.register(tool)
    for tool in create_web_tools():
        tool_registry.register(tool)

    tracker.log("Infrastructure ready - Provider, AgentManager, Registry, Tools registered")

    # === PHASE 2: Create Specialized Agents ===
    tracker.log("Phase 2: Spawning specialized agents...")

    # Create Research Agent (Tool Agent specialized for web requests)
    research_agent = await registry.create_agent(
        AgentType.TOOL,
        name="MarketResearchAgent"
    )
    tracker.record_agent(research_agent.id, "tool", research_agent.name)
    tracker.log(f"  Spawned: {research_agent.name} (ID: {research_agent.id[:8]}...)")

    # Create Data Analyst Agent
    analyst_agent = await registry.create_agent(
        AgentType.TOOL,
        name="DataAnalystAgent"
    )
    tracker.record_agent(analyst_agent.id, "tool", analyst_agent.name)
    tracker.log(f"  Spawned: {analyst_agent.name} (ID: {analyst_agent.id[:8]}...)")

    # Create Report Writer Agent
    writer_agent = await registry.create_agent(
        AgentType.TOOL,
        name="ReportWriterAgent"
    )
    tracker.record_agent(writer_agent.id, "tool", writer_agent.name)
    tracker.log(f"  Spawned: {writer_agent.name} (ID: {writer_agent.id[:8]}...)")

    # Create Critic Agent for quality validation
    critic_agent = await registry.create_agent(
        AgentType.CRITIC,
        name="QualityReviewerAgent"
    )
    tracker.record_agent(critic_agent.id, "critic", critic_agent.name)
    tracker.log(f"  Spawned: {critic_agent.name} (ID: {critic_agent.id[:8]}...)")

    print()

    # === PHASE 3: Execute Market Research Tasks ===
    tracker.log("Phase 3: Executing market research tasks...")

    from src.core.message import AgentMessage, MessageType, Constraints

    # Task 1: Fetch cryptocurrency market data
    tracker.log("  Task 1: Fetching cryptocurrency market data...")

    research_task = Task(
        description="""Fetch real-time cryptocurrency market data for the top 5 cryptocurrencies.

Use the http_get tool to fetch data from: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=5&page=1

Extract and format the following for each coin:
- Name and symbol
- Current price in USD
- Market cap
- 24h price change percentage
- 24h trading volume

Return the data in a clear, structured format.""",
        goal_id="market-research-goal",
        objective="Gather current cryptocurrency market data",
    )

    research_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=research_agent.id,
        recipient_type="tool",
        goal_id="market-research-goal",
        task_id=research_task.id,
        task=research_task,
        content={},
    )

    research_result = await research_agent.execute(research_message)

    if research_result.success:
        tracker.record_task("Fetch cryptocurrency market data", "completed", research_agent.name)
        tracker.record_tool("http_get", True, str(research_result.result)[:500])
        tracker.log(f"    [SUCCESS] Data fetched - {research_result.tokens_used} tokens used")

        # Extract the actual data for next step
        market_data = research_result.result
    else:
        tracker.record_task("Fetch cryptocurrency market data", "failed", research_agent.name)
        tracker.log(f"    [FAILED] {research_result.error}")
        market_data = None

    # Record outcome for learning
    await registry.record_task_outcome(
        agent_id=research_agent.id,
        task=research_task,
        success=research_result.success,
        tokens_used=research_result.tokens_used,
        execution_time_ms=int(research_result.execution_time_seconds * 1000),
        error=research_result.error,
    )

    # Task 2: Analyze the market data
    tracker.log("  Task 2: Analyzing market data and generating insights...")

    analysis_task = Task(
        description=f"""Analyze the following cryptocurrency market data and provide insights:

Market Data:
{json.dumps(market_data, indent=2) if isinstance(market_data, dict) else str(market_data)[:2000]}

Provide analysis including:
1. Market Overview: Total market cap of top 5 coins
2. Price Leaders: Which coins have the highest prices
3. Performance Analysis: Best and worst performers (24h change)
4. Volume Analysis: Trading activity comparison
5. Investment Insights: Brief recommendations based on data

Format the analysis in a clear, professional manner.""",
        goal_id="market-research-goal",
        objective="Analyze cryptocurrency market data",
    )

    analysis_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=analyst_agent.id,
        recipient_type="tool",
        goal_id="market-research-goal",
        task_id=analysis_task.id,
        task=analysis_task,
        content={},
    )

    analysis_result = await analyst_agent.execute(analysis_message)

    if analysis_result.success:
        tracker.record_task("Analyze market data", "completed", analyst_agent.name)
        tracker.log(f"    [SUCCESS] Analysis complete - {analysis_result.tokens_used} tokens used")
        analysis_content = analysis_result.result
    else:
        tracker.record_task("Analyze market data", "failed", analyst_agent.name)
        tracker.log(f"    [FAILED] {analysis_result.error}")
        analysis_content = None

    await registry.record_task_outcome(
        agent_id=analyst_agent.id,
        task=analysis_task,
        success=analysis_result.success,
        tokens_used=analysis_result.tokens_used,
        execution_time_ms=int(analysis_result.execution_time_seconds * 1000),
        error=analysis_result.error,
    )

    # Task 3: Generate comprehensive report
    tracker.log("  Task 3: Generating comprehensive market research report...")

    report_task = Task(
        description=f"""Create a comprehensive market research report and save it to a file.

Use the write_file tool to save the report to: crypto_market_report.md

The report should include:

# Cryptocurrency Market Research Report
## Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

### Executive Summary
[Brief overview of the current market state]

### Market Data
{json.dumps(market_data, indent=2) if isinstance(market_data, dict) else str(market_data)[:1500]}

### Analysis
{str(analysis_content)[:1500] if analysis_content else "Analysis pending"}

### Methodology
- Data Source: CoinGecko API
- Analysis: AI-powered market analysis
- Generated by: Agent Village Market Research System

### Disclaimer
This report is for informational purposes only and should not be considered financial advice.

Save this complete report to the file.""",
        goal_id="market-research-goal",
        objective="Generate and save market research report",
    )

    report_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=writer_agent.id,
        recipient_type="tool",
        goal_id="market-research-goal",
        task_id=report_task.id,
        task=report_task,
        content={},
    )

    report_result = await writer_agent.execute(report_message)

    if report_result.success:
        tracker.record_task("Generate market report", "completed", writer_agent.name)
        tracker.record_tool("write_file", True, "crypto_market_report.md")
        tracker.log(f"    [SUCCESS] Report generated - {report_result.tokens_used} tokens used")
        report_content = report_result.result
    else:
        tracker.record_task("Generate market report", "failed", writer_agent.name)
        tracker.log(f"    [FAILED] {report_result.error}")
        report_content = None

    await registry.record_task_outcome(
        agent_id=writer_agent.id,
        task=report_task,
        success=report_result.success,
        tokens_used=report_result.tokens_used,
        execution_time_ms=int(report_result.execution_time_seconds * 1000),
        error=report_result.error,
    )

    print()

    # === PHASE 4: Quality Review ===
    tracker.log("Phase 4: Quality review by Critic agent...")

    review_task = Task(
        description="Review the generated market research report for quality",
        goal_id="market-research-goal",
        objective="Validate report quality",
    )

    review_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=critic_agent.id,
        recipient_type="critic",
        goal_id="market-research-goal",
        task_id=review_task.id,
        task=review_task,
        content={
            "content_to_review": report_content,
            "original_task": "Generate comprehensive cryptocurrency market research report",
            "expected_output": "Professional market research report with data, analysis, and insights",
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

    # === PHASE 5: Check Agent Learning ===
    tracker.log("Phase 5: Verifying agent learning and persistence...")

    all_profiles = agent_manager.get_all_profiles()
    for profile in all_profiles:
        if profile.performance.total_tasks > 0:
            tracker.log(f"  {profile.name}: {profile.performance.total_tasks} tasks, "
                       f"{profile.performance.success_rate:.0%} success rate")

    print()

    # === PHASE 6: Collect Results ===
    tracker.end_time = datetime.now()
    tracker.log("Phase 6: Collecting final results...")

    # Store results
    tracker.results = [
        {
            "phase": "Data Fetching",
            "success": research_result.success,
            "tokens_used": research_result.tokens_used,
            "output_preview": str(market_data)[:500] if market_data else "N/A"
        },
        {
            "phase": "Data Analysis",
            "success": analysis_result.success,
            "tokens_used": analysis_result.tokens_used,
            "output_preview": str(analysis_content)[:500] if analysis_content else "N/A"
        },
        {
            "phase": "Report Generation",
            "success": report_result.success,
            "tokens_used": report_result.tokens_used,
            "output_preview": str(report_content)[:500] if report_content else "N/A"
        },
        {
            "phase": "Quality Review",
            "success": review_result.success,
            "quality_score": tracker.quality_metrics.get("quality_score", 0),
            "validity": tracker.quality_metrics.get("validity", "unknown")
        }
    ]

    # Read the generated report if it exists
    generated_report = None
    try:
        from pathlib import Path
        report_path = Path.cwd() / "workspace" / "crypto_market_report.md"
        if report_path.exists():
            generated_report = report_path.read_text()
            tracker.log(f"  Generated report saved at: {report_path}")
    except Exception as e:
        tracker.log(f"  Could not read generated report: {e}")

    # Cleanup
    await registry.shutdown_all()

    # Print Summary
    print()
    print("=" * 80)
    print("USE CASE 1 SUMMARY: MARKET RESEARCH AUTOMATION")
    print("=" * 80)
    print(f"Duration: {tracker.to_dict()['duration_seconds']:.2f} seconds")
    print(f"Agents Spawned: {len(tracker.agents_spawned)}")
    print(f"Tasks Executed: {len(tracker.tasks_executed)}")
    print(f"Tools Used: {len(tracker.tools_used)}")
    print(f"Quality Score: {tracker.quality_metrics.get('quality_score', 'N/A')}/100")
    print("=" * 80)

    return tracker.to_dict(), generated_report


if __name__ == "__main__":
    results, report = asyncio.run(test_market_research())

    # Save results to JSON for documentation
    with open("usecase1_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nResults saved to usecase1_results.json")

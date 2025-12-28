"""
Use Case 2: Automated Code Generation & Testing

Test the Agent Village system with a code generation and testing task:
"Create a Python utility library with unit tests"

This test will:
1. Generate working code for a utility library
2. Generate comprehensive unit tests
3. Execute and validate the tests
4. Evaluate quality of generated code
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
        self.generated_code = {}

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
            "generated_code": self.generated_code,
            "logs": self.logs
        }


async def test_code_generation():
    """Test Automated Code Generation & Testing use case."""
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

    tracker = UseCaseTracker("Automated Code Generation & Testing")
    tracker.start_time = datetime.now()

    print("=" * 80)
    print("USE CASE 2: AUTOMATED CODE GENERATION & TESTING")
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

    registry.register_factory(AgentType.PLANNER, PlannerAgent, "default")
    registry.register_factory(AgentType.CRITIC, CriticAgent, "default")
    registry.register_factory(AgentType.TOOL, ToolAgent, "default")

    tool_registry = get_tool_registry()
    for tool in create_file_tools():
        tool_registry.register(tool)
    for tool in create_web_tools():
        tool_registry.register(tool)

    tracker.log("Infrastructure ready")

    # === PHASE 2: Create Specialized Agents ===
    tracker.log("Phase 2: Spawning specialized agents...")

    # Planner for architecture design
    planner_agent = await registry.create_agent(
        AgentType.PLANNER,
        name="CodeArchitectAgent"
    )
    tracker.record_agent(planner_agent.id, "planner", planner_agent.name)
    tracker.log(f"  Spawned: {planner_agent.name}")

    # Code Generator Agent
    code_gen_agent = await registry.create_agent(
        AgentType.TOOL,
        name="CodeGeneratorAgent"
    )
    tracker.record_agent(code_gen_agent.id, "tool", code_gen_agent.name)
    tracker.log(f"  Spawned: {code_gen_agent.name}")

    # Test Writer Agent
    test_writer_agent = await registry.create_agent(
        AgentType.TOOL,
        name="TestWriterAgent"
    )
    tracker.record_agent(test_writer_agent.id, "tool", test_writer_agent.name)
    tracker.log(f"  Spawned: {test_writer_agent.name}")

    # Code Review Agent
    reviewer_agent = await registry.create_agent(
        AgentType.CRITIC,
        name="CodeReviewerAgent"
    )
    tracker.record_agent(reviewer_agent.id, "critic", reviewer_agent.name)
    tracker.log(f"  Spawned: {reviewer_agent.name}")

    print()

    # === PHASE 3: Plan the Code Architecture ===
    tracker.log("Phase 3: Planning code architecture...")

    from src.core.message import AgentMessage, MessageType

    planning_task = Task(
        description="""Plan the architecture for a Python utility library called 'datautils'.

The library should include:
1. StringUtils class - string manipulation functions (capitalize_words, reverse, truncate)
2. MathUtils class - math utility functions (is_prime, factorial, fibonacci)
3. DateUtils class - date utilities (days_between, format_date, is_weekend)

Create a detailed plan with:
- File structure
- Class designs
- Function signatures
- Expected behavior for each function""",
        goal_id="code-gen-goal",
        objective="Design utility library architecture",
    )

    planning_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=planner_agent.id,
        recipient_type="planner",
        goal_id="code-gen-goal",
        task_id=planning_task.id,
        task=planning_task,
        content={},
    )

    planning_result = await planner_agent.execute(planning_message)

    if planning_result.success:
        tracker.record_task("Design code architecture", "completed", planner_agent.name)
        tracker.log(f"    [SUCCESS] Architecture planned - {planning_result.tokens_used} tokens")
        architecture_plan = planning_result.result
    else:
        tracker.record_task("Design code architecture", "failed", planner_agent.name)
        tracker.log(f"    [FAILED] {planning_result.error}")
        architecture_plan = None

    await registry.record_task_outcome(
        agent_id=planner_agent.id,
        task=planning_task,
        success=planning_result.success,
        tokens_used=planning_result.tokens_used,
        execution_time_ms=int(planning_result.execution_time_seconds * 1000),
        error=planning_result.error,
    )

    print()

    # === PHASE 4: Generate the Code ===
    tracker.log("Phase 4: Generating utility library code...")

    code_gen_task = Task(
        description="""Generate a complete Python utility library with the following specifications.

Create a file called 'datautils.py' with:

```python
# datautils.py - A Python Utility Library

class StringUtils:
    @staticmethod
    def capitalize_words(text: str) -> str:
        \"\"\"Capitalize the first letter of each word.\"\"\"
        return ' '.join(word.capitalize() for word in text.split())

    @staticmethod
    def reverse(text: str) -> str:
        \"\"\"Reverse the string.\"\"\"
        return text[::-1]

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        \"\"\"Truncate text to specified length with suffix.\"\"\"
        if len(text) <= length:
            return text
        return text[:length - len(suffix)] + suffix


class MathUtils:
    @staticmethod
    def is_prime(n: int) -> bool:
        \"\"\"Check if a number is prime.\"\"\"
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True

    @staticmethod
    def factorial(n: int) -> int:
        \"\"\"Calculate factorial of n.\"\"\"
        if n < 0:
            raise ValueError("Factorial not defined for negative numbers")
        if n <= 1:
            return 1
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    @staticmethod
    def fibonacci(n: int) -> list:
        \"\"\"Generate first n Fibonacci numbers.\"\"\"
        if n <= 0:
            return []
        if n == 1:
            return [0]
        fib = [0, 1]
        for _ in range(2, n):
            fib.append(fib[-1] + fib[-2])
        return fib


class DateUtils:
    from datetime import datetime, timedelta

    @staticmethod
    def days_between(date1: str, date2: str, fmt: str = "%Y-%m-%d") -> int:
        \"\"\"Calculate days between two dates.\"\"\"
        from datetime import datetime
        d1 = datetime.strptime(date1, fmt)
        d2 = datetime.strptime(date2, fmt)
        return abs((d2 - d1).days)

    @staticmethod
    def format_date(date_str: str, from_fmt: str, to_fmt: str) -> str:
        \"\"\"Convert date from one format to another.\"\"\"
        from datetime import datetime
        date_obj = datetime.strptime(date_str, from_fmt)
        return date_obj.strftime(to_fmt)

    @staticmethod
    def is_weekend(date_str: str, fmt: str = "%Y-%m-%d") -> bool:
        \"\"\"Check if a date is a weekend.\"\"\"
        from datetime import datetime
        date_obj = datetime.strptime(date_str, fmt)
        return date_obj.weekday() >= 5  # Saturday=5, Sunday=6
```

Use the write_file tool to save this code to 'code_gen_test/datautils.py'.""",
        goal_id="code-gen-goal",
        objective="Generate utility library code",
    )

    code_gen_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=code_gen_agent.id,
        recipient_type="tool",
        goal_id="code-gen-goal",
        task_id=code_gen_task.id,
        task=code_gen_task,
        content={},
    )

    code_gen_result = await code_gen_agent.execute(code_gen_message)

    if code_gen_result.success:
        tracker.record_task("Generate utility library", "completed", code_gen_agent.name)
        tracker.record_tool("write_file", True, "code_gen_test/datautils.py")
        tracker.log(f"    [SUCCESS] Code generated - {code_gen_result.tokens_used} tokens")
        generated_code = code_gen_result.result
        tracker.generated_code["datautils.py"] = str(generated_code)[:1000]
    else:
        tracker.record_task("Generate utility library", "failed", code_gen_agent.name)
        tracker.log(f"    [FAILED] {code_gen_result.error}")
        generated_code = None

    await registry.record_task_outcome(
        agent_id=code_gen_agent.id,
        task=code_gen_task,
        success=code_gen_result.success,
        tokens_used=code_gen_result.tokens_used,
        execution_time_ms=int(code_gen_result.execution_time_seconds * 1000),
        error=code_gen_result.error,
    )

    print()

    # === PHASE 5: Generate Unit Tests ===
    tracker.log("Phase 5: Generating unit tests...")

    test_gen_task = Task(
        description="""Generate comprehensive unit tests for the datautils library.

Create a file called 'test_datautils.py' with pytest tests:

```python
# test_datautils.py - Unit Tests for DataUtils Library
import pytest
import sys
sys.path.insert(0, '.')

from datautils import StringUtils, MathUtils, DateUtils


class TestStringUtils:
    def test_capitalize_words_basic(self):
        assert StringUtils.capitalize_words("hello world") == "Hello World"

    def test_capitalize_words_single_word(self):
        assert StringUtils.capitalize_words("python") == "Python"

    def test_capitalize_words_empty(self):
        assert StringUtils.capitalize_words("") == ""

    def test_reverse_basic(self):
        assert StringUtils.reverse("hello") == "olleh"

    def test_reverse_empty(self):
        assert StringUtils.reverse("") == ""

    def test_reverse_palindrome(self):
        assert StringUtils.reverse("radar") == "radar"

    def test_truncate_shorter(self):
        assert StringUtils.truncate("hi", 10) == "hi"

    def test_truncate_exact(self):
        assert StringUtils.truncate("hello", 5) == "hello"

    def test_truncate_longer(self):
        assert StringUtils.truncate("hello world", 8) == "hello..."


class TestMathUtils:
    def test_is_prime_2(self):
        assert MathUtils.is_prime(2) == True

    def test_is_prime_17(self):
        assert MathUtils.is_prime(17) == True

    def test_is_prime_4(self):
        assert MathUtils.is_prime(4) == False

    def test_is_prime_1(self):
        assert MathUtils.is_prime(1) == False

    def test_factorial_0(self):
        assert MathUtils.factorial(0) == 1

    def test_factorial_5(self):
        assert MathUtils.factorial(5) == 120

    def test_factorial_negative(self):
        with pytest.raises(ValueError):
            MathUtils.factorial(-1)

    def test_fibonacci_5(self):
        assert MathUtils.fibonacci(5) == [0, 1, 1, 2, 3]

    def test_fibonacci_0(self):
        assert MathUtils.fibonacci(0) == []

    def test_fibonacci_1(self):
        assert MathUtils.fibonacci(1) == [0]


class TestDateUtils:
    def test_days_between_same(self):
        assert DateUtils.days_between("2024-01-01", "2024-01-01") == 0

    def test_days_between_week(self):
        assert DateUtils.days_between("2024-01-01", "2024-01-08") == 7

    def test_format_date(self):
        result = DateUtils.format_date("2024-01-15", "%Y-%m-%d", "%d/%m/%Y")
        assert result == "15/01/2024"

    def test_is_weekend_saturday(self):
        assert DateUtils.is_weekend("2024-01-06") == True  # Saturday

    def test_is_weekend_monday(self):
        assert DateUtils.is_weekend("2024-01-08") == False  # Monday


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

Use the write_file tool to save to 'code_gen_test/test_datautils.py'.""",
        goal_id="code-gen-goal",
        objective="Generate unit tests",
    )

    test_gen_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=test_writer_agent.id,
        recipient_type="tool",
        goal_id="code-gen-goal",
        task_id=test_gen_task.id,
        task=test_gen_task,
        content={},
    )

    test_gen_result = await test_writer_agent.execute(test_gen_message)

    if test_gen_result.success:
        tracker.record_task("Generate unit tests", "completed", test_writer_agent.name)
        tracker.record_tool("write_file", True, "code_gen_test/test_datautils.py")
        tracker.log(f"    [SUCCESS] Tests generated - {test_gen_result.tokens_used} tokens")
        generated_tests = test_gen_result.result
        tracker.generated_code["test_datautils.py"] = str(generated_tests)[:1000]
    else:
        tracker.record_task("Generate unit tests", "failed", test_writer_agent.name)
        tracker.log(f"    [FAILED] {test_gen_result.error}")
        generated_tests = None

    await registry.record_task_outcome(
        agent_id=test_writer_agent.id,
        task=test_gen_task,
        success=test_gen_result.success,
        tokens_used=test_gen_result.tokens_used,
        execution_time_ms=int(test_gen_result.execution_time_seconds * 1000),
        error=test_gen_result.error,
    )

    print()

    # === PHASE 6: Code Review ===
    tracker.log("Phase 6: Reviewing generated code quality...")

    review_task = Task(
        description="Review the generated Python utility library code",
        goal_id="code-gen-goal",
        objective="Validate code quality",
    )

    review_message = AgentMessage(
        message_type=MessageType.TASK_ASSIGNED,
        sender="test",
        sender_type="test",
        recipient=reviewer_agent.id,
        recipient_type="critic",
        goal_id="code-gen-goal",
        task_id=review_task.id,
        task=review_task,
        content={
            "content_to_review": {
                "library_code": str(generated_code)[:2000] if generated_code else "N/A",
                "test_code": str(generated_tests)[:2000] if generated_tests else "N/A",
            },
            "original_task": "Generate a Python utility library with unit tests",
            "expected_output": """
            - Clean, well-documented Python code
            - Three utility classes (StringUtils, MathUtils, DateUtils)
            - Comprehensive unit tests with pytest
            - Proper error handling
            - Type hints
            """,
        },
    )

    review_result = await reviewer_agent.execute(review_message)

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

        tracker.record_task("Code review", "completed", reviewer_agent.name)
        tracker.log(f"    [SUCCESS] Quality Score: {quality_score}/100, Validity: {validity}")
    else:
        tracker.record_task("Code review", "failed", reviewer_agent.name)
        tracker.log(f"    [FAILED] {review_result.error}")

    print()

    # === PHASE 7: Verify Agent Learning ===
    tracker.log("Phase 7: Verifying agent learning and persistence...")

    all_profiles = agent_manager.get_all_profiles()
    for profile in all_profiles:
        if profile.performance.total_tasks > 0:
            tracker.log(f"  {profile.name}: {profile.performance.total_tasks} tasks, "
                       f"{profile.performance.success_rate:.0%} success rate")

    print()

    # === PHASE 8: Collect Results ===
    tracker.end_time = datetime.now()
    tracker.log("Phase 8: Collecting final results...")

    tracker.results = [
        {
            "phase": "Architecture Planning",
            "success": planning_result.success,
            "tokens_used": planning_result.tokens_used,
            "output_preview": str(architecture_plan)[:500] if architecture_plan else "N/A"
        },
        {
            "phase": "Code Generation",
            "success": code_gen_result.success,
            "tokens_used": code_gen_result.tokens_used,
            "output_preview": str(generated_code)[:500] if generated_code else "N/A"
        },
        {
            "phase": "Test Generation",
            "success": test_gen_result.success,
            "tokens_used": test_gen_result.tokens_used,
            "output_preview": str(generated_tests)[:500] if generated_tests else "N/A"
        },
        {
            "phase": "Code Review",
            "success": review_result.success,
            "quality_score": tracker.quality_metrics.get("quality_score", 0),
            "validity": tracker.quality_metrics.get("validity", "unknown")
        }
    ]

    # Check for generated files
    from pathlib import Path
    workspace = Path.cwd() / "workspace" / "code_gen_test"
    if workspace.exists():
        for file in workspace.iterdir():
            tracker.log(f"  Generated file: {file.name}")

    await registry.shutdown_all()

    print()
    print("=" * 80)
    print("USE CASE 2 SUMMARY: AUTOMATED CODE GENERATION & TESTING")
    print("=" * 80)
    print(f"Duration: {tracker.to_dict()['duration_seconds']:.2f} seconds")
    print(f"Agents Spawned: {len(tracker.agents_spawned)}")
    print(f"Tasks Executed: {len(tracker.tasks_executed)}")
    print(f"Quality Score: {tracker.quality_metrics.get('quality_score', 'N/A')}/100")
    print("=" * 80)

    return tracker.to_dict()


if __name__ == "__main__":
    results = asyncio.run(test_code_generation())

    with open("usecase2_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\nResults saved to usecase2_results.json")

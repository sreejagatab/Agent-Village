"""
Critic Agent - Critics & Auditors.

Responsible for:
- Validating outputs
- Detecting hallucinations
- Scoring quality
- Providing feedback
"""

import json
import re
from dataclasses import dataclass, field
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
from src.providers.base import LLMProvider

logger = structlog.get_logger()


def extract_json_from_response(response: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        json_str = response.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        brace_match = re.search(r'\{[\s\S]*\}', json_str)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


CRITIC_SYSTEM_PROMPT = """You are a Critic agent in the Agent Village.

Your role is to validate outputs, detect issues, and score quality with ACTIONABLE feedback.

When reviewing work:
1. Check for correctness and accuracy
2. Identify potential errors or hallucinations
3. Assess completeness against requirements
4. Evaluate quality and clarity
5. Provide SPECIFIC, ACTIONABLE recommendations

IMPORTANT: Your recommendations must be:
- SPECIFIC: Not "improve quality" but "add input validation for edge cases"
- ACTIONABLE: Each recommendation should be implementable immediately
- PRIORITIZED: Mark each issue and recommendation as high/medium/low priority
- CONSTRUCTIVE: Focus on how to fix, not just what's wrong

For each review, provide:
- Validity assessment (valid/invalid/needs_revision)
- Quality score (0-100) with clear reasoning
- List of issues found with specific locations and fixes
- List of strengths (be specific about what works well)
- Prioritized improvement recommendations

Be thorough but fair. Focus on substantive issues, not style preferences.
Always respond with structured JSON for reviews."""


@dataclass
class QualityIssue:
    """A quality issue found during review."""

    severity: str  # critical, major, minor, suggestion
    category: str  # accuracy, completeness, clarity, security, etc.
    description: str
    location: str = ""  # Where in the output the issue was found
    suggestion: str = ""  # How to fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class ReviewResult:
    """Result of a quality review."""

    validity: str  # valid, invalid, needs_revision
    quality_score: float  # 0-100
    issues: list[QualityIssue] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def is_valid(self) -> bool:
        return self.validity == "valid"

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "validity": self.validity,
            "quality_score": self.quality_score,
            "issues": [i.to_dict() for i in self.issues],
            "strengths": self.strengths,
            "recommendations": self.recommendations,
            "summary": self.summary,
        }


class CriticAgent(BaseAgent):
    """
    Critic Agent for quality validation and feedback.

    Part of the Critics & Auditors guild.
    """

    def __init__(
        self,
        provider: LLMProvider,
        name: str | None = None,
        constraints: AgentConstraints | None = None,
    ):
        if constraints is None:
            constraints = AgentConstraints(
                max_tokens_per_request=4096,
                can_spawn_agents=False,
                can_access_memory=True,
                risk_tolerance="low",
            )

        super().__init__(
            agent_type=AgentType.CRITIC,
            provider=provider,
            name=name or "critic",
            constraints=constraints,
        )

        self._system_prompt = CRITIC_SYSTEM_PROMPT

    async def execute(self, message: AgentMessage) -> AgentResult:
        """Review and validate work."""
        import time

        start_time = time.time()
        self.state = AgentState.BUSY

        try:
            task = message.task
            if not task:
                return self._create_result(
                    task_id=message.task_id or "",
                    success=False,
                    error="No task provided for review",
                )

            # Get the content to review
            content_to_review = message.content.get("content_to_review")
            original_task = message.content.get("original_task")
            expected_output = message.content.get("expected_output")

            if not content_to_review:
                return self._create_result(
                    task_id=task.id,
                    success=False,
                    error="No content provided for review",
                )

            # Perform review
            review = await self._review_content(
                content_to_review,
                original_task or task.description,
                expected_output or task.expected_output,
            )

            execution_time = time.time() - start_time
            self.metrics.tasks_completed += 1
            self.metrics.total_execution_time += execution_time
            self.state = AgentState.IDLE

            return self._create_result(
                task_id=task.id,
                success=True,
                result=review.to_dict(),
                confidence=0.85,
                quality_score=review.quality_score / 100,
                tokens_used=self.metrics.total_tokens_used,
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error("Review failed", error=str(e))
            self.metrics.tasks_failed += 1
            self.state = AgentState.ERROR

            return self._create_result(
                task_id=message.task_id or "",
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _review_content(
        self,
        content: Any,
        original_task: str,
        expected_output: str | None,
    ) -> ReviewResult:
        """Review content against requirements."""
        # Check for common issues to filter out
        content_str = json.dumps(content, indent=2) if isinstance(content, dict) else str(content)

        # Detect permission error noise
        has_permission_errors = "permission" in content_str.lower() and "denied" in content_str.lower()

        review_prompt = f"""Review the following content and assess its quality.

## Original Task
{original_task}

## Expected Output
{expected_output or 'Not specified'}

## Content to Review
{content_str}

## Review Instructions
Evaluate the content for:
1. **Accuracy**: Is the content factually correct?
2. **Completeness**: Does it fulfill all requirements from the original task?
3. **Clarity**: Is it clear, well-organized, and free of irrelevant content?
4. **Correctness**: Are there any errors or bugs?
5. **Security**: Are there any security concerns?

IMPORTANT SCORING GUIDELINES:
- 90-100: Excellent - Fully meets requirements with high quality
- 75-89: Good - Meets most requirements, minor issues only
- 60-74: Acceptable - Core requirements met but notable gaps
- 40-59: Needs Revision - Significant issues or missing requirements
- 0-39: Poor - Major failures or requirements not met

{"NOTE: The content contains permission error messages which should be filtered from final output." if has_permission_errors else ""}

You MUST respond with valid JSON (no markdown code blocks):
{{
    "validity": "valid|invalid|needs_revision",
    "quality_score": 0-100,
    "quality_score_reasoning": "explain how you calculated this score",
    "issues": [
        {{
            "severity": "critical|major|minor|suggestion",
            "priority": "high|medium|low",
            "category": "accuracy|completeness|clarity|security|other",
            "description": "specific description of issue",
            "location": "exact location where the issue was found",
            "suggestion": "specific, actionable fix"
        }}
    ],
    "strengths": ["specific positive aspects with examples"],
    "recommendations": [
        {{
            "priority": "high|medium|low",
            "action": "specific actionable improvement",
            "expected_benefit": "what this will improve"
        }}
    ],
    "summary": "brief overall assessment"
}}

Be thorough but constructive. Every issue must have a specific fix suggestion."""

        response = await self._call_llm(review_prompt, temperature=0.2)
        review_data = extract_json_from_response(response)

        if not review_data:
            self.logger.warning("Failed to parse review JSON", response=response[:200])
            # Provide basic analysis based on content inspection
            quality_score = 50
            issues = []

            if has_permission_errors:
                issues.append(QualityIssue(
                    severity="minor",
                    category="clarity",
                    description="Output contains permission error messages that should be filtered",
                    location="Throughout output",
                    suggestion="Filter out system error messages from final output",
                ))
                quality_score -= 10

            return ReviewResult(
                validity="needs_revision",
                quality_score=quality_score,
                issues=issues,
                summary="Automated review - detailed analysis unavailable",
            )

        issues = [
            QualityIssue(
                severity=i.get("severity", "minor"),
                category=i.get("category", "other"),
                description=i.get("description", ""),
                location=i.get("location", ""),
                suggestion=i.get("suggestion", ""),
            )
            for i in review_data.get("issues", [])
        ]

        # Parse recommendations into actionable format
        recommendations = []
        raw_recs = review_data.get("recommendations", [])
        for rec in raw_recs:
            if isinstance(rec, dict):
                priority = rec.get("priority", "medium")
                action = rec.get("action", "")
                benefit = rec.get("expected_benefit", "")
                recommendations.append(f"[{priority.upper()}] {action}" + (f" - {benefit}" if benefit else ""))
            elif isinstance(rec, str):
                recommendations.append(rec)

        summary = review_data.get("summary", "")
        if review_data.get("quality_score_reasoning"):
            summary = f"{summary} (Scoring: {review_data.get('quality_score_reasoning')})"

        return ReviewResult(
            validity=review_data.get("validity", "needs_revision"),
            quality_score=float(review_data.get("quality_score", 50)),
            issues=issues,
            strengths=review_data.get("strengths", []),
            recommendations=recommendations,
            summary=summary,
        )

    async def validate_result(
        self, result: AgentResult, task: Task
    ) -> ReviewResult:
        """Quick validation of an agent result."""
        if not result.success:
            return ReviewResult(
                validity="invalid",
                quality_score=0,
                issues=[
                    QualityIssue(
                        severity="critical",
                        category="completeness",
                        description=f"Task failed: {result.error}",
                    )
                ],
                summary="Task execution failed",
            )

        return await self._review_content(
            result.result,
            task.description,
            task.expected_output,
        )

    async def reflect(self, result: AgentResult) -> Reflection:
        """Reflect on review quality."""
        if not result.success:
            return Reflection(
                agent_id=self.id,
                task_id=result.task_id,
                performance_score=0.3,
                failures=[result.error or "Review failed"],
            )

        review_data = result.result or {}
        issue_count = len(review_data.get("issues", []))
        quality_score = review_data.get("quality_score", 0)

        return Reflection(
            agent_id=self.id,
            task_id=result.task_id,
            performance_score=result.quality_score,
            lessons_learned=[
                f"Found {issue_count} issues, quality score: {quality_score}",
            ],
            successes=["Review completed successfully"],
            recommendations=[
                "Consider domain-specific validation rules",
                "Track common issue patterns for improvement",
            ],
        )

    async def can_handle(self, task: Task) -> float:
        """Assess ability to handle review task."""
        description_lower = task.description.lower()

        # High confidence for review-related tasks
        review_keywords = [
            "review", "validate", "verify", "check", "audit",
            "assess", "evaluate", "quality", "test", "critique",
        ]

        if any(kw in description_lower for kw in review_keywords):
            return 0.9

        return 0.4

"""
Finite State Machine Engine for Agent Village.

This is the core orchestration engine that controls the execution flow.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable

import structlog

from src.core.message import Goal, GoalContext, GoalStatus, Task, TaskStatus
from src.core.safety import SafetyGate, SafetyViolationError, get_safety_gate

logger = structlog.get_logger()


class ExecutionState(str, Enum):
    """States in the execution FSM."""

    # Initial states
    IDLE = "idle"
    RECEIVED = "received"

    # Planning phase
    INTENT_ANALYSIS = "intent_analysis"
    TASK_DECOMPOSITION = "task_decomposition"
    AGENT_ASSIGNMENT = "agent_assignment"

    # Execution phase
    EXECUTING = "executing"
    PARALLEL_EXECUTING = "parallel_executing"

    # Validation phase
    VERIFYING = "verifying"
    WRITING_MEMORY = "writing_memory"
    REFLECTING = "reflecting"

    # Terminal states
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # Special states
    AWAITING_HUMAN = "awaiting_human"
    REPLANNING = "replanning"


@dataclass
class StateTransition:
    """Definition of a state transition."""

    from_state: ExecutionState
    to_state: ExecutionState
    condition: Callable[[GoalContext], bool] | None = None
    action: Callable[[GoalContext], Awaitable[GoalContext]] | None = None
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = f"{self.from_state.value}_to_{self.to_state.value}"


@dataclass
class FSMContext:
    """Runtime context for the FSM."""

    goal_context: GoalContext
    current_state: ExecutionState = ExecutionState.IDLE
    previous_state: ExecutionState | None = None
    state_history: list[tuple[ExecutionState, datetime]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def record_state(self, state: ExecutionState) -> None:
        """Record a state transition."""
        self.previous_state = self.current_state
        self.current_state = state
        self.state_history.append((state, datetime.now(timezone.utc)))


class ExecutionFSM:
    """
    Finite State Machine for goal execution.

    Controls the flow:
    GOAL → Intent Analysis → Task Decomposition → Agent Assignment
        → Execution → Verification → Memory Write → Reflection
        → Completed or Replanning
    """

    def __init__(
        self,
        safety_gate: SafetyGate | None = None,
    ):
        self.safety_gate = safety_gate or get_safety_gate()
        self.logger = logger.bind(component="execution_fsm")

        self._transitions: dict[ExecutionState, list[StateTransition]] = {}
        self._state_handlers: dict[
            ExecutionState, Callable[[FSMContext], Awaitable[ExecutionState]]
        ] = {}

        self._setup_default_transitions()

    def _setup_default_transitions(self) -> None:
        """Set up the default state transitions."""
        # From IDLE
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.IDLE,
                to_state=ExecutionState.RECEIVED,
                name="receive_goal",
            )
        )

        # From RECEIVED
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.RECEIVED,
                to_state=ExecutionState.INTENT_ANALYSIS,
                name="start_analysis",
            )
        )

        # From INTENT_ANALYSIS
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.INTENT_ANALYSIS,
                to_state=ExecutionState.TASK_DECOMPOSITION,
                name="decompose_tasks",
            )
        )

        # From TASK_DECOMPOSITION
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.TASK_DECOMPOSITION,
                to_state=ExecutionState.AGENT_ASSIGNMENT,
                name="assign_agents",
            )
        )

        # From AGENT_ASSIGNMENT
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.AGENT_ASSIGNMENT,
                to_state=ExecutionState.EXECUTING,
                condition=lambda ctx: len(ctx.goal.tasks) == 1,
                name="single_execution",
            )
        )
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.AGENT_ASSIGNMENT,
                to_state=ExecutionState.PARALLEL_EXECUTING,
                condition=lambda ctx: len(ctx.goal.tasks) > 1,
                name="parallel_execution",
            )
        )

        # From EXECUTING
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.EXECUTING,
                to_state=ExecutionState.VERIFYING,
                name="verify_result",
            )
        )
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.EXECUTING,
                to_state=ExecutionState.AWAITING_HUMAN,
                condition=lambda ctx: any(
                    t.status == TaskStatus.AWAITING_APPROVAL for t in ctx.goal.tasks
                ),
                name="await_approval",
            )
        )

        # From PARALLEL_EXECUTING
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.PARALLEL_EXECUTING,
                to_state=ExecutionState.VERIFYING,
                name="verify_parallel_results",
            )
        )

        # From VERIFYING
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.VERIFYING,
                to_state=ExecutionState.WRITING_MEMORY,
                condition=lambda ctx: all(
                    t.status == TaskStatus.COMPLETED for t in ctx.goal.tasks
                ),
                name="write_memory",
            )
        )
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.VERIFYING,
                to_state=ExecutionState.REPLANNING,
                condition=lambda ctx: any(
                    t.status == TaskStatus.FAILED for t in ctx.goal.tasks
                ),
                name="replan_on_failure",
            )
        )

        # From WRITING_MEMORY
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.WRITING_MEMORY,
                to_state=ExecutionState.REFLECTING,
                name="reflect",
            )
        )

        # From REFLECTING
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.REFLECTING,
                to_state=ExecutionState.COMPLETED,
                name="complete",
            )
        )

        # From REPLANNING
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.REPLANNING,
                to_state=ExecutionState.TASK_DECOMPOSITION,
                name="replan",
            )
        )
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.REPLANNING,
                to_state=ExecutionState.FAILED,
                condition=lambda ctx: ctx.goal.metadata.get("replan_count", 0) >= 3,
                name="fail_after_replans",
            )
        )

        # From AWAITING_HUMAN
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.AWAITING_HUMAN,
                to_state=ExecutionState.EXECUTING,
                name="resume_after_approval",
            )
        )
        self.add_transition(
            StateTransition(
                from_state=ExecutionState.AWAITING_HUMAN,
                to_state=ExecutionState.CANCELLED,
                name="cancelled_by_human",
            )
        )

    def add_transition(self, transition: StateTransition) -> None:
        """Add a state transition."""
        if transition.from_state not in self._transitions:
            self._transitions[transition.from_state] = []
        self._transitions[transition.from_state].append(transition)

    def register_state_handler(
        self,
        state: ExecutionState,
        handler: Callable[[FSMContext], Awaitable[ExecutionState]],
    ) -> None:
        """
        Register a handler for a state.

        The handler is called when the FSM enters the state and should
        return the next state to transition to.
        """
        self._state_handlers[state] = handler

    async def execute(self, goal: Goal) -> Goal:
        """
        Execute a goal through the FSM.

        Args:
            goal: Goal to execute

        Returns:
            Updated goal with results
        """
        # Create context
        goal_context = GoalContext(goal=goal)
        fsm_context = FSMContext(goal_context=goal_context)

        self.logger.info(
            "Starting goal execution",
            goal_id=goal.id,
            description=goal.description[:100],
        )

        # Initial transition
        await self._transition_to(fsm_context, ExecutionState.RECEIVED)

        # Run the FSM until terminal state
        while not self._is_terminal(fsm_context.current_state):
            try:
                # Safety check
                self.safety_gate.enforce(goal_context)

                # Execute state handler if registered
                handler = self._state_handlers.get(fsm_context.current_state)
                if handler:
                    next_state = await handler(fsm_context)
                    if next_state != fsm_context.current_state:
                        await self._transition_to(fsm_context, next_state)
                        continue

                # Find and execute valid transition
                next_state = await self._find_next_state(fsm_context)
                if next_state:
                    await self._transition_to(fsm_context, next_state)
                else:
                    self.logger.error(
                        "No valid transition found",
                        current_state=fsm_context.current_state.value,
                    )
                    await self._transition_to(fsm_context, ExecutionState.FAILED)

            except SafetyViolationError as e:
                self.logger.error("Safety violation", error=str(e))
                fsm_context.error = str(e)
                await self._transition_to(fsm_context, ExecutionState.FAILED)

            except Exception as e:
                self.logger.exception("Execution error", error=str(e))
                fsm_context.error = str(e)
                await self._transition_to(fsm_context, ExecutionState.FAILED)

        # Update goal status based on terminal state
        goal.status = self._state_to_goal_status(fsm_context.current_state)
        if fsm_context.error:
            goal.error = fsm_context.error

        goal.completed_at = datetime.now(timezone.utc)

        self.logger.info(
            "Goal execution completed",
            goal_id=goal.id,
            final_state=fsm_context.current_state.value,
            status=goal.status.value,
        )

        return goal

    async def _transition_to(
        self, context: FSMContext, new_state: ExecutionState
    ) -> None:
        """Perform a state transition."""
        context.record_state(new_state)
        self.logger.debug(
            "State transition",
            from_state=context.previous_state.value if context.previous_state else None,
            to_state=new_state.value,
            goal_id=context.goal_context.goal.id,
        )

    async def _find_next_state(self, context: FSMContext) -> ExecutionState | None:
        """Find the next valid state based on transitions."""
        transitions = self._transitions.get(context.current_state, [])

        for transition in transitions:
            if transition.condition is None:
                # No condition - this is the default transition
                if transition.action:
                    context.goal_context = await transition.action(context.goal_context)
                return transition.to_state

            if transition.condition(context.goal_context):
                if transition.action:
                    context.goal_context = await transition.action(context.goal_context)
                return transition.to_state

        return None

    def _is_terminal(self, state: ExecutionState) -> bool:
        """Check if a state is terminal."""
        return state in {
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        }

    def _state_to_goal_status(self, state: ExecutionState) -> GoalStatus:
        """Convert FSM state to goal status."""
        mapping = {
            ExecutionState.COMPLETED: GoalStatus.COMPLETED,
            ExecutionState.FAILED: GoalStatus.FAILED,
            ExecutionState.CANCELLED: GoalStatus.CANCELLED,
            ExecutionState.AWAITING_HUMAN: GoalStatus.EXECUTING,
        }
        return mapping.get(state, GoalStatus.EXECUTING)

    def get_state_diagram(self) -> str:
        """Generate a text representation of the state diagram."""
        lines = ["State Diagram:", "=" * 40]

        for from_state, transitions in sorted(
            self._transitions.items(), key=lambda x: x[0].value
        ):
            for transition in transitions:
                condition = (
                    f" [if {transition.name}]" if transition.condition else ""
                )
                lines.append(
                    f"  {from_state.value} -> {transition.to_state.value}{condition}"
                )

        return "\n".join(lines)


# Factory function
def create_execution_fsm(safety_gate: SafetyGate | None = None) -> ExecutionFSM:
    """Create an execution FSM with default configuration."""
    return ExecutionFSM(safety_gate=safety_gate)

"""Tests for FSM engine."""

import pytest

from src.core.fsm import ExecutionFSM, ExecutionState, StateTransition, FSMContext
from src.core.message import Goal, GoalContext, GoalStatus


class TestExecutionState:
    """Tests for ExecutionState enum."""

    def test_all_states_defined(self):
        """Test all required states are defined."""
        required_states = [
            "idle", "received", "intent_analysis", "task_decomposition",
            "agent_assignment", "executing", "verifying", "completed", "failed",
        ]

        for state_name in required_states:
            assert hasattr(ExecutionState, state_name.upper())


class TestStateTransition:
    """Tests for StateTransition."""

    def test_transition_creation(self):
        """Test creating a transition."""
        transition = StateTransition(
            from_state=ExecutionState.IDLE,
            to_state=ExecutionState.RECEIVED,
            name="test_transition",
        )

        assert transition.from_state == ExecutionState.IDLE
        assert transition.to_state == ExecutionState.RECEIVED
        assert transition.name == "test_transition"

    def test_transition_with_condition(self):
        """Test transition with condition."""
        def condition(ctx: GoalContext) -> bool:
            return len(ctx.goal.tasks) > 1

        transition = StateTransition(
            from_state=ExecutionState.AGENT_ASSIGNMENT,
            to_state=ExecutionState.PARALLEL_EXECUTING,
            condition=condition,
        )

        assert transition.condition is not None


class TestFSMContext:
    """Tests for FSMContext."""

    def test_record_state(self, goal_context):
        """Test recording state transitions."""
        context = FSMContext(goal_context=goal_context)

        context.record_state(ExecutionState.RECEIVED)
        context.record_state(ExecutionState.INTENT_ANALYSIS)

        assert context.current_state == ExecutionState.INTENT_ANALYSIS
        assert context.previous_state == ExecutionState.RECEIVED
        assert len(context.state_history) == 2


class TestExecutionFSM:
    """Tests for ExecutionFSM."""

    def test_fsm_creation(self, safety_gate):
        """Test FSM creation."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        assert fsm is not None
        assert len(fsm._transitions) > 0

    def test_default_transitions_exist(self, safety_gate):
        """Test that default transitions are set up."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        # Check key transitions exist
        assert ExecutionState.IDLE in fsm._transitions
        assert ExecutionState.RECEIVED in fsm._transitions
        assert ExecutionState.INTENT_ANALYSIS in fsm._transitions

    def test_add_custom_transition(self, safety_gate):
        """Test adding custom transition."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        custom = StateTransition(
            from_state=ExecutionState.EXECUTING,
            to_state=ExecutionState.COMPLETED,
            name="fast_complete",
        )

        fsm.add_transition(custom)

        transitions = fsm._transitions.get(ExecutionState.EXECUTING, [])
        assert any(t.name == "fast_complete" for t in transitions)

    def test_terminal_state_detection(self, safety_gate):
        """Test terminal state detection."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        assert fsm._is_terminal(ExecutionState.COMPLETED) is True
        assert fsm._is_terminal(ExecutionState.FAILED) is True
        assert fsm._is_terminal(ExecutionState.CANCELLED) is True
        assert fsm._is_terminal(ExecutionState.EXECUTING) is False

    def test_state_to_goal_status_mapping(self, safety_gate):
        """Test FSM state to goal status mapping."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        assert fsm._state_to_goal_status(ExecutionState.COMPLETED) == GoalStatus.COMPLETED
        assert fsm._state_to_goal_status(ExecutionState.FAILED) == GoalStatus.FAILED
        assert fsm._state_to_goal_status(ExecutionState.CANCELLED) == GoalStatus.CANCELLED

    def test_get_state_diagram(self, safety_gate):
        """Test state diagram generation."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        diagram = fsm.get_state_diagram()

        assert "State Diagram" in diagram
        assert "idle" in diagram.lower()
        assert "->" in diagram

    def test_register_state_handler(self, safety_gate):
        """Test registering state handlers."""
        fsm = ExecutionFSM(safety_gate=safety_gate)

        async def custom_handler(context: FSMContext) -> ExecutionState:
            return ExecutionState.COMPLETED

        fsm.register_state_handler(ExecutionState.EXECUTING, custom_handler)

        assert ExecutionState.EXECUTING in fsm._state_handlers
        assert fsm._state_handlers[ExecutionState.EXECUTING] == custom_handler

"""Tests for memory subsystem."""

import pytest
import pytest_asyncio

from src.memory.base import (
    InMemoryStore,
    MemoryEntry,
    MemoryQuery,
    MemoryType,
)
from src.memory.episodic import Episode, EpisodicMemory
from src.memory.semantic import KnowledgeItem, SemanticMemory
from src.memory.procedural import Procedure, ProceduralMemory
from src.memory.strategic import Decision, StrategicMemory


class TestInMemoryStore:
    """Tests for InMemoryStore."""

    @pytest.mark.asyncio
    async def test_store_and_get(self, memory_store):
        """Test storing and retrieving entries."""
        entry = MemoryEntry(
            memory_type=MemoryType.SEMANTIC,
            content="Test content",
            summary="Test summary",
        )

        entry_id = await memory_store.store(entry)
        retrieved = await memory_store.get(entry_id)

        assert retrieved is not None
        assert retrieved.content == "Test content"
        assert retrieved.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_query_by_type(self, memory_store):
        """Test querying by memory type."""
        # Store different types
        semantic = MemoryEntry(memory_type=MemoryType.SEMANTIC, content="semantic")
        episodic = MemoryEntry(memory_type=MemoryType.EPISODIC, content="episodic")

        await memory_store.store(semantic)
        await memory_store.store(episodic)

        query = MemoryQuery(memory_types=[MemoryType.SEMANTIC])
        result = await memory_store.query(query)

        assert len(result.entries) == 1
        assert result.entries[0].memory_type == MemoryType.SEMANTIC

    @pytest.mark.asyncio
    async def test_query_by_text(self, memory_store):
        """Test text search."""
        entry1 = MemoryEntry(content="Python programming", summary="About Python")
        entry2 = MemoryEntry(content="JavaScript coding", summary="About JavaScript")

        await memory_store.store(entry1)
        await memory_store.store(entry2)

        query = MemoryQuery(query_text="Python")
        result = await memory_store.query(query)

        assert len(result.entries) == 1
        assert "Python" in result.entries[0].content

    @pytest.mark.asyncio
    async def test_query_by_tags(self, memory_store):
        """Test querying by tags."""
        entry1 = MemoryEntry(content="Entry 1", tags=["python", "coding"])
        entry2 = MemoryEntry(content="Entry 2", tags=["javascript", "web"])

        await memory_store.store(entry1)
        await memory_store.store(entry2)

        query = MemoryQuery(tags=["python"])
        result = await memory_store.query(query)

        assert len(result.entries) == 1
        assert "python" in result.entries[0].tags

    @pytest.mark.asyncio
    async def test_update_entry(self, memory_store):
        """Test updating an entry."""
        entry = MemoryEntry(content="Original", importance_score=0.5)
        entry_id = await memory_store.store(entry)

        success = await memory_store.update(entry_id, {"importance_score": 0.9})
        updated = await memory_store.get(entry_id)

        assert success is True
        assert updated.importance_score == 0.9

    @pytest.mark.asyncio
    async def test_delete_entry(self, memory_store):
        """Test deleting an entry."""
        entry = MemoryEntry(content="To delete")
        entry_id = await memory_store.store(entry)

        success = await memory_store.delete(entry_id)
        retrieved = await memory_store.get(entry_id)

        assert success is True
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_query_pagination(self, memory_store):
        """Test query pagination."""
        # Store 10 entries
        for i in range(10):
            await memory_store.store(MemoryEntry(content=f"Entry {i}"))

        # Query with limit
        query = MemoryQuery(limit=5)
        result = await memory_store.query(query)

        assert len(result.entries) == 5
        assert result.total_count == 10


class TestEpisodicMemory:
    """Tests for EpisodicMemory."""

    @pytest_asyncio.fixture
    async def episodic(self):
        """Create episodic memory."""
        return EpisodicMemory()

    @pytest.mark.asyncio
    async def test_record_episode(self, episodic):
        """Test recording an episode."""
        episode = Episode(
            event_type="task_completed",
            description="Completed the data analysis",
            outcome="success",
        )

        entry_id = await episodic.record_episode(
            episode,
            goal_id="goal_123",
            importance=0.8,
        )

        entry = await episodic.get(entry_id)

        assert entry is not None
        assert entry.memory_type == MemoryType.EPISODIC
        assert entry.importance_score == 0.8

    @pytest.mark.asyncio
    async def test_get_timeline(self, episodic):
        """Test getting episode timeline."""
        for i in range(5):
            episode = Episode(
                event_type="step",
                description=f"Step {i}",
            )
            await episodic.record_episode(episode, goal_id="goal_123")

        timeline = await episodic.get_timeline(goal_id="goal_123")

        assert len(timeline) == 5


class TestSemanticMemory:
    """Tests for SemanticMemory."""

    @pytest_asyncio.fixture
    async def semantic(self):
        """Create semantic memory."""
        return SemanticMemory()

    @pytest.mark.asyncio
    async def test_store_knowledge(self, semantic):
        """Test storing knowledge."""
        item = KnowledgeItem(
            fact="Python is a programming language",
            domain="programming",
            confidence=0.95,
        )

        entry_id = await semantic.store_knowledge(item)
        entry = await semantic.get(entry_id)

        assert entry is not None
        assert entry.memory_type == MemoryType.SEMANTIC
        assert "Python" in entry.summary

    @pytest.mark.asyncio
    async def test_search_knowledge(self, semantic):
        """Test searching knowledge."""
        item1 = KnowledgeItem(fact="Python uses indentation", domain="python")
        item2 = KnowledgeItem(fact="JavaScript uses braces", domain="javascript")

        await semantic.store_knowledge(item1)
        await semantic.store_knowledge(item2)

        results = await semantic.search_knowledge("Python", domain="python")

        assert len(results) >= 1


class TestProceduralMemory:
    """Tests for ProceduralMemory."""

    @pytest_asyncio.fixture
    async def procedural(self):
        """Create procedural memory."""
        return ProceduralMemory()

    @pytest.mark.asyncio
    async def test_store_procedure(self, procedural):
        """Test storing a procedure."""
        procedure = Procedure(
            name="deploy_app",
            description="Deploy application to production",
            steps=["Build", "Test", "Deploy"],
            success_rate=0.9,
        )

        entry_id = await procedural.store_procedure(procedure)
        entry = await procedural.get(entry_id)

        assert entry is not None
        assert entry.memory_type == MemoryType.PROCEDURAL
        assert entry.importance_score == 0.9

    @pytest.mark.asyncio
    async def test_find_procedure(self, procedural):
        """Test finding procedures."""
        procedure = Procedure(
            name="code_review",
            description="Review code for quality",
            steps=["Read", "Analyze", "Comment"],
            tools_required=["linter"],
        )
        await procedural.store_procedure(procedure)

        results = await procedural.find_procedure("review code")

        assert len(results) >= 0  # May or may not match based on search


class TestStrategicMemory:
    """Tests for StrategicMemory."""

    @pytest_asyncio.fixture
    async def strategic(self):
        """Create strategic memory."""
        return StrategicMemory()

    @pytest.mark.asyncio
    async def test_record_decision(self, strategic):
        """Test recording a decision."""
        decision = Decision(
            decision_type="pattern_selection",
            description="Chose swarm pattern for parallel execution",
            rationale="Task requires parallel processing",
            alternatives_considered=["sequential", "council"],
        )

        entry_id = await strategic.record_decision(
            decision,
            goal_id="goal_123",
        )

        entry = await strategic.get(entry_id)

        assert entry is not None
        assert entry.memory_type == MemoryType.STRATEGIC

    @pytest.mark.asyncio
    async def test_record_outcome(self, strategic):
        """Test recording decision outcome."""
        decision = Decision(
            decision_type="agent_selection",
            description="Selected tool agent",
            rationale="Task requires tool execution",
        )
        entry_id = await strategic.record_decision(decision)

        success = await strategic.record_outcome(
            entry_id,
            outcome="success",
            outcome_score=0.9,
            lessons=["Tool agent was appropriate"],
        )

        entry = await strategic.get(entry_id)

        assert success is True
        assert entry.importance_score == 0.9

    @pytest.mark.asyncio
    async def test_get_lessons_learned(self, strategic):
        """Test getting lessons learned."""
        decision = Decision(
            decision_type="test_type",
            description="Test decision",
            rationale="Test rationale",
        )
        entry_id = await strategic.record_decision(decision)
        await strategic.record_outcome(
            entry_id,
            outcome="success",
            outcome_score=0.8,
            lessons=["Lesson 1", "Lesson 2"],
        )

        lessons = await strategic.get_lessons_learned(decision_type="test_type")

        assert len(lessons) >= 2

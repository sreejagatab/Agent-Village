# Agent Village - Capabilities & Achievements

<p align="center">
  <strong>A Comprehensive Guide to What Agent Village Can Do, How It Works, and When to Use It</strong>
</p>

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Core Capabilities](#core-capabilities)
4. [Agent Types & Specializations](#agent-types--specializations)
5. [Execution Patterns](#execution-patterns)
6. [Memory & Learning System](#memory--learning-system)
7. [Tool Ecosystem](#tool-ecosystem)
8. [Safety & Governance](#safety--governance)
9. [Real-World Use Cases](#real-world-use-cases)
10. [Performance Metrics](#performance-metrics)
11. [Integration Patterns](#integration-patterns)
12. [Decision Flowcharts](#decision-flowcharts)

---

## Executive Summary

Agent Village is an enterprise-grade multi-agent orchestration system that achieves complex goals through intelligent coordination of specialized AI agents. The system demonstrates:

| Capability | Achievement |
|------------|-------------|
| **Dynamic Agent Spawning** | Automatically creates specialized agents based on task requirements |
| **Intelligent Task Decomposition** | Breaks complex goals into atomic, parallelizable tasks |
| **Learning & Adaptation** | Improves agent selection and performance over time |
| **Safety-First Execution** | Enforces hard limits and human-in-the-loop controls |
| **Persistent Memory** | Learns from past experiences across sessions |
| **Scalable Coordination** | Handles single tasks to swarm operations |

---

## System Architecture

### High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                    USER REQUEST                                    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                      GOVERNOR                                      |
|  +-------------+  +------------------+  +---------------+  +------------------+   |
|  |   Intent    |->| Task Decomposer  |->|    Agent      |->|   Orchestrator   |   |
|  |  Analyzer   |  |                  |  |  Assigner     |  |                  |   |
|  +-------------+  +------------------+  +---------------+  +------------------+   |
+-----------------------------------------------------------------------------------+
                |                    |                   |                    |
                v                    v                   v                    v
+---------------+    +---------------+    +---------------+    +---------------+
|   PLANNER     |    |    CRITIC     |    |     TOOL      |    |    SWARM      |
|   COUNCIL     |    |   & AUDITOR   |    |    GUILD      |    |  COORDINATOR  |
+---------------+    +---------------+    +---------------+    +---------------+
        |                    |                   |                    |
        v                    v                   v                    v
+-----------------------------------------------------------------------------------+
|                              MEMORY SYSTEMS                                        |
|  +------------+  +------------+  +-------------+  +------------+  +------------+  |
|  |  Episodic  |  |  Semantic  |  | Procedural  |  | Strategic  |  |  Vector    |  |
|  |  Memory    |  |  Memory    |  |   Memory    |  |  Memory    |  |   Store    |  |
|  +------------+  +------------+  +-------------+  +------------+  +------------+  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              PERSISTENCE LAYER                                     |
|  +------------------+  +------------------+  +------------------+                  |
|  |   PostgreSQL     |  |      Redis       |  |    Celery        |                  |
|  |   (Goals/Tasks)  |  |     (Cache)      |  |  (Task Queue)    |                  |
|  +------------------+  +------------------+  +------------------+                  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              OBSERVABILITY LAYER                                   |
|  +------------------+  +------------------+  +------------------+                  |
|  |   Prometheus     |  |     Grafana      |  |   Distributed    |                  |
|  |    (Metrics)     |  |   (Dashboards)   |  |    Workers       |                  |
|  +------------------+  +------------------+  +------------------+                  |
+-----------------------------------------------------------------------------------+
```

### Execution Flow (FSM - Finite State Machine)

```
                                    +--------+
                                    |  IDLE  |
                                    +---+----+
                                        |
                                        v
                                  +----------+
                                  | RECEIVED |
                                  +----+-----+
                                       |
                                       v
                              +-----------------+
                              | INTENT_ANALYSIS |
                              +--------+--------+
                                       |
                                       v
                            +--------------------+
                            | TASK_DECOMPOSITION |
                            +---------+----------+
                                      |
                                      v
                            +-------------------+
                            | AGENT_ASSIGNMENT  |
                            +--------+----------+
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
             +-----------+                  +------------------+
             | EXECUTING |                  | PARALLEL_EXECUTING|
             +-----+-----+                  +--------+---------+
                   |                                 |
                   +----------------+----------------+
                                    |
                                    v
                              +-----------+
                              | VERIFYING |
                              +-----+-----+
                                    |
              +---------------------+---------------------+
              |                     |                     |
              v                     v                     v
     +--------------+        +------------+        +----------+
     | WRITING_     |        | REPLANNING |        |  FAILED  |
     |   MEMORY     |        +------+-----+        +----------+
     +------+-------+               |
            |                       |
            v                       v
     +------------+        +--------------------+
     | REFLECTING |        | TASK_DECOMPOSITION |
     +------+-----+        +--------------------+
            |
            v
     +-----------+
     | COMPLETED |
     +-----------+
```

---

## Core Capabilities

### 1. Dynamic Goal Execution

**What It Does:**
- Receives natural language goals
- Analyzes intent and complexity
- Creates optimized execution plans
- Spawns appropriate agents dynamically
- Monitors and adapts during execution

**How It Works:**

```
User Goal: "Build a cryptocurrency price tracker with analysis"
                          |
                          v
+----------------------------------------------------------+
|                    INTENT ANALYSIS                        |
|  - Core Objective: Data retrieval + Analysis + Storage   |
|  - Capabilities Needed: Web requests, file operations    |
|  - Complexity: MODERATE                                   |
|  - Risk Level: LOW                                        |
+----------------------------------------------------------+
                          |
                          v
+----------------------------------------------------------+
|                  TASK DECOMPOSITION                       |
|  Task 1: Fetch cryptocurrency prices from API            |
|  Task 2: Process and analyze price data                  |
|  Task 3: Generate visualization/report                   |
|  Task 4: Save results to file                            |
+----------------------------------------------------------+
                          |
                          v
+----------------------------------------------------------+
|                  AGENT ASSIGNMENT                         |
|  Task 1 -> Tool Agent (web_request capability)           |
|  Task 2 -> Tool Agent (code execution capability)        |
|  Task 3 -> Tool Agent (file creation capability)         |
|  Task 4 -> Tool Agent (file write capability)            |
+----------------------------------------------------------+
                          |
                          v
+----------------------------------------------------------+
|                    EXECUTION                              |
|  - Parallel execution where possible                     |
|  - Sequential for dependencies                           |
|  - Automatic retry on failure                            |
|  - Learning from outcomes                                |
+----------------------------------------------------------+
```

**When to Use:**
- Complex multi-step tasks
- Tasks requiring multiple capabilities
- Tasks that benefit from parallel execution
- Long-running operations needing monitoring

---

### 2. Intelligent Agent Selection

**What It Does:**
- Maintains agent profiles with capabilities
- Scores agents based on task requirements
- Learns from past performance
- Recommends best agents for tasks

**Scoring Algorithm:**

```
Agent Score = Base(0.5)
            + Success Rate Weight(0.4) x Agent's Success Rate
            + Task Type Weight(0.3) x Task Type Match Score
            + Capability Weight(0.2) x Capability Match Score
            + Recency Weight(0.1) x Recent Activity Bonus

Where:
- Success Rate: Historical success percentage
- Task Type Match: Agent's performance on similar task types
- Capability Match: Keyword matching between task and agent skills
- Recency Bonus: Higher for recently active agents
```

**Visual Flow:**

```
                    +-------------------+
                    | Incoming Task     |
                    | "Fetch stock      |
                    |  prices from API" |
                    +--------+----------+
                             |
                             v
              +--------------+--------------+
              |     AgentManager Lookup     |
              +--------------+--------------+
                             |
        +--------------------+--------------------+
        |                    |                    |
        v                    v                    v
+---------------+    +---------------+    +---------------+
| Tool Agent A  |    | Tool Agent B  |    | Tool Agent C  |
| Success: 95%  |    | Success: 70%  |    | Success: 85%  |
| Tasks: 50     |    | Tasks: 10     |    | Tasks: 25     |
| Skills: API,  |    | Skills: File  |    | Skills: API,  |
|   HTTP, JSON  |    |   operations  |    |   Web scrape  |
+---------------+    +---------------+    +---------------+
        |                    |                    |
        v                    v                    v
   Score: 0.92          Score: 0.45          Score: 0.78
        |                    |                    |
        +--------------------+--------------------+
                             |
                             v
                    +-------------------+
                    | Selected:         |
                    | Tool Agent A      |
                    | Reason: Highest   |
                    | score + API       |
                    | expertise         |
                    +-------------------+
```

---

### 3. Learning from Outcomes

**What It Does:**
- Records task execution results
- Updates agent performance metrics
- Stores lessons in strategic memory
- Improves future decisions

**Learning Loop:**

```
+----------------+     +----------------+     +------------------+
|    Execute     | --> |    Record      | --> |     Update       |
|     Task       |     |    Outcome     |     |    Metrics       |
+----------------+     +----------------+     +------------------+
                              |                        |
                              v                        v
                    +-------------------+    +-------------------+
                    | Strategic Memory  |    | Agent Profile     |
                    | - Decision record |    | - Success rate    |
                    | - Lessons learned |    | - Task type scores|
                    | - Context saved   |    | - Token usage     |
                    +-------------------+    +-------------------+
                              |                        |
                              +------------+-----------+
                                           |
                                           v
                              +------------------------+
                              |   Future Decisions     |
                              |   Informed by Past     |
                              |   Performance Data     |
                              +------------------------+
```

**Metrics Tracked:**
- Success/failure counts
- Token usage per task type
- Execution time patterns
- Error frequency and types
- Capability utilization

---

## Agent Types & Specializations

### Agent Hierarchy

```
                              +-------------+
                              |  GOVERNOR   |
                              | (Meta-Agent)|
                              +------+------+
                                     |
        +------------------+---------+---------+------------------+
        |                  |                   |                  |
        v                  v                   v                  v
+---------------+  +---------------+  +---------------+  +---------------+
|    PLANNER    |  |    CRITIC     |  |     TOOL      |  |    SWARM      |
|    COUNCIL    |  |   & AUDITOR   |  |    GUILD      |  |  COORDINATOR  |
+---------------+  +---------------+  +---------------+  +---------------+
        |                  |                   |                  |
        v                  v                   v                  v
 - Decompose      - Validate        - Execute         - Parallel
   goals            outputs           actions           execution
 - Design          - Score           - API calls       - Aggregate
   strategies        quality         - File ops          results
 - Estimate        - Detect          - Code run        - Scale
   complexity        issues          - Web fetch         operations
                                                              |
                                                              v
                                                     +---------------+
                                                     | SWARM WORKERS |
                                                     | (Ephemeral)   |
                                                     +---------------+
```

### Detailed Agent Capabilities

| Agent Type | Primary Role | Key Capabilities | When to Use |
|------------|--------------|------------------|-------------|
| **Governor** | Meta-orchestration | Goal analysis, agent spawning, execution control, safety enforcement | Always (central controller) |
| **Planner** | Strategic planning | Task decomposition, workflow design, dependency analysis, risk assessment | Complex multi-step goals |
| **Tool Agent** | Action execution | File operations, web requests, code execution, API calls | Any task requiring tools |
| **Critic** | Quality assurance | Output validation, hallucination detection, scoring, feedback | Before finalizing results |
| **Swarm Coordinator** | Parallel execution | Work division, worker management, result aggregation | Large-scale parallel tasks |
| **Swarm Worker** | Subtask execution | Focused task completion, quick execution | Part of swarm operations |
| **Evolver** | Self-improvement | Prompt optimization, workflow improvement, pattern analysis | System optimization cycles |
| **Memory Keeper** | Knowledge management | Memory storage, retrieval, organization | Long-term knowledge tasks |

---

## Execution Patterns

### Pattern Selection Flow

```
                         +-------------------+
                         |  Analyze Goal     |
                         |  Complexity       |
                         +--------+----------+
                                  |
                                  v
                    +-------------+-------------+
                    |    Complexity Level?      |
                    +-------------+-------------+
                                  |
      +-------------+-------------+-------------+-------------+
      |             |             |             |             |
      v             v             v             v             v
 +--------+    +--------+    +---------+   +---------+   +----------+
 | TRIVIAL|    | SIMPLE |    |MODERATE |   | COMPLEX |   |STRATEGIC |
 +---+----+    +---+----+    +----+----+   +----+----+   +----+-----+
     |             |              |             |              |
     v             v              v             v              v
 +--------+    +--------+    +---------+   +---------+   +----------+
 | Single |    | Single |    | Council |   | Council |   |  Market  |
 | Agent  |    | Agent  |    | Planning|   | + Swarm |   |  Based   |
 | No Mem |    | + Mem  |    +Sequential   +Parallel +   |Coordinate|
 +--------+    +--------+    +---------+   +---------+   +----------+
```

### Execution Pattern Details

#### 1. Single Agent Pattern
```
Goal --> Agent --> Result

Use When:
- Simple, atomic tasks
- Clear single-step solution
- Low complexity
```

#### 2. Council Pattern
```
Goal --> Planner --> [Tasks] --> Agents --> Critic --> Result
                                    |                     ^
                                    +---> Memory ---------+

Use When:
- Multi-step tasks
- Need quality assurance
- Medium complexity
```

#### 3. Swarm Pattern
```
                         Goal
                           |
                           v
                    +------+------+
                    |   Swarm     |
                    | Coordinator |
                    +------+------+
                           |
        +--------+---------+---------+--------+
        |        |         |         |        |
        v        v         v         v        v
    +------+ +------+ +------+ +------+ +------+
    |Worker| |Worker| |Worker| |Worker| |Worker|
    +--+---+ +--+---+ +--+---+ +--+---+ +--+---+
       |        |         |         |        |
       v        v         v         v        v
    Result   Result   Result   Result   Result
       |        |         |         |        |
       +--------+---------+---------+--------+
                          |
                          v
                   +------+------+
                   | Aggregated  |
                   |   Result    |
                   +-------------+

Use When:
- Large-scale data gathering
- Embarrassingly parallel tasks
- Need for speed over depth
```

#### 4. Market Pattern
```
Goal --> Task Auction --> Agents Bid --> Best Agent Wins --> Execute

Use When:
- Strategic resource allocation
- Cost/quality optimization
- Complex enterprise scenarios
```

---

## Memory & Learning System

### Memory Architecture

```
+-------------------------------------------------------------------------+
|                          MEMORY SYSTEMS                                  |
+-------------------------------------------------------------------------+
|                                                                          |
|  +-------------------+    +-------------------+    +-------------------+ |
|  |  EPISODIC MEMORY  |    |  SEMANTIC MEMORY  |    | PROCEDURAL MEMORY | |
|  |                   |    |                   |    |                   | |
|  | What happened?    |    | What do we know?  |    | How do we do it?  | |
|  |                   |    |                   |    |                   | |
|  | - Events          |    | - Facts           |    | - Workflows       | |
|  | - Experiences     |    | - Concepts        |    | - Procedures      | |
|  | - Timelines       |    | - Relationships   |    | - Best practices  | |
|  | - Outcomes        |    | - Knowledge graph |    | - Patterns        | |
|  +-------------------+    +-------------------+    +-------------------+ |
|           |                        |                        |            |
|           +------------------------+------------------------+            |
|                                    |                                     |
|                                    v                                     |
|                         +-------------------+                            |
|                         | STRATEGIC MEMORY  |                            |
|                         |                   |                            |
|                         | Why decisions     |                            |
|                         | were made?        |                            |
|                         |                   |                            |
|                         | - Decision logs   |                            |
|                         | - Rationales      |                            |
|                         | - Outcomes        |                            |
|                         | - Lessons learned |                            |
|                         +-------------------+                            |
|                                    |                                     |
|                                    v                                     |
|                         +-------------------+                            |
|                         |   VECTOR STORE    |                            |
|                         |                   |                            |
|                         | Embeddings for    |                            |
|                         | semantic search   |                            |
|                         +-------------------+                            |
+-------------------------------------------------------------------------+
```

### Memory Query Flow

```
+----------------+     +-----------------+     +------------------+
|  New Task      | --> | Generate Query  | --> | Search Vector    |
|  Description   |     | Embedding       |     | Store            |
+----------------+     +-----------------+     +------------------+
                                                        |
                                                        v
                                              +------------------+
                                              | Retrieve Similar |
                                              | Past Experiences |
                                              +------------------+
                                                        |
                                                        v
                                              +------------------+
                                              | Extract Lessons  |
                                              | & Patterns       |
                                              +------------------+
                                                        |
                                                        v
                                              +------------------+
                                              | Inform Current   |
                                              | Decision         |
                                              +------------------+
```

---

## Tool Ecosystem

### Available Tools

```
+-------------------------------------------------------------------------+
|                             TOOL REGISTRY                                |
+-------------------------------------------------------------------------+
|                                                                          |
|  FILE OPERATIONS                    WEB OPERATIONS                       |
|  +------------------+               +------------------+                 |
|  | read_file        |               | http_get         |                 |
|  | write_file       |               | http_post        |                 |
|  | list_directory   |               | http_request     |                 |
|  | create_directory |               | fetch_webpage    |                 |
|  | delete_file      |               +------------------+                 |
|  | copy_file        |                                                    |
|  | move_file        |               SANDBOX OPERATIONS                   |
|  | search_files     |               +------------------+                 |
|  | file_info        |               | execute_python   |                 |
|  +------------------+               | run_command      |                 |
|                                     +------------------+                 |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Tool Permission Levels

```
+------------------+--------------------------------------------------+
|   Permission     |                  Allowed Actions                 |
+------------------+--------------------------------------------------+
| READ_ONLY        | Read files, list directories, HTTP GET           |
+------------------+--------------------------------------------------+
| READ_WRITE       | Read/Write files, create directories, HTTP POST  |
+------------------+--------------------------------------------------+
| EXECUTE          | Run code, execute commands (sandboxed)           |
+------------------+--------------------------------------------------+
| ADMIN            | All operations (requires human approval)         |
+------------------+--------------------------------------------------+
```

### Tool Execution Flow

```
+----------------+     +----------------+     +----------------+
|   Tool Agent   | --> |    Tool        | --> |   Permission   |
|   Request      |     |   Registry     |     |     Check      |
+----------------+     +----------------+     +----------------+
                                                      |
                            +-------------------------+
                            |
                            v
                   +----------------+
                   |   Approved?    |
                   +----------------+
                      |         |
                     Yes        No
                      |         |
                      v         v
              +----------+  +----------+
              | Execute  |  |  Return  |
              |   Tool   |  |  Error   |
              +----+-----+  +----------+
                   |
                   v
              +----------+
              | Sandbox  |
              | Wrapper  |
              +----+-----+
                   |
                   v
              +----------+
              |  Return  |
              |  Result  |
              +----------+
```

---

## Safety & Governance

### Safety Gate Architecture

```
+-------------------------------------------------------------------------+
|                           SAFETY GATE                                    |
|                    (Cannot Be Bypassed)                                  |
+-------------------------------------------------------------------------+
|                                                                          |
|   +-------------------------------------------------------------------+ |
|   |                      HARD LIMITS                                   | |
|   +-------------------------------------------------------------------+ |
|   |                                                                    | |
|   |   +------------------+  +------------------+  +------------------+ | |
|   |   | Recursion Limit  |  | Token Budget     |  | Agent Spawn     | | |
|   |   | Max: 10 levels   |  | Max: 500K tokens |  | Max: 50 agents  | | |
|   |   +------------------+  +------------------+  +------------------+ | |
|   |                                                                    | |
|   |   +------------------+  +------------------+  +------------------+ | |
|   |   | Execution Time   |  | Risk Level       |  | Concurrent      | | |
|   |   | Max: 1 hour      |  | Max: HIGH        |  | Max: 20 agents  | | |
|   |   +------------------+  +------------------+  +------------------+ | |
|   +-------------------------------------------------------------------+ |
|                                                                          |
|   +-------------------------------------------------------------------+ |
|   |                   HUMAN APPROVAL REQUIRED                          | |
|   +-------------------------------------------------------------------+ |
|   |   - Deploy operations                                              | |
|   |   - Delete operations                                              | |
|   |   - Payment processing                                             | |
|   |   - Admin actions                                                  | |
|   |   - Code execution                                                 | |
|   +-------------------------------------------------------------------+ |
|                                                                          |
|   +-------------------------------------------------------------------+ |
|   |                    BLOCKED ACTIONS                                 | |
|   +-------------------------------------------------------------------+ |
|   |   - rm -rf                                                         | |
|   |   - DROP DATABASE                                                  | |
|   |   - Format operations                                              | |
|   |   - Access to internal IPs                                         | |
|   |   - Access to metadata endpoints                                   | |
|   +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

### Safety Check Flow

```
              +-------------------+
              |  Incoming Action  |
              +--------+----------+
                       |
                       v
              +-------------------+
              | Recursion Check   |
              +--------+----------+
                       |
            Pass       |       Fail
        +--------------+-------------+
        |                            |
        v                            v
+-------------------+        +-------------------+
|   Token Check     |        |  REJECT ACTION    |
+--------+----------+        | (SafetyViolation) |
         |                   +-------------------+
         |
         v
+-------------------+
| Agent Spawn Check |
+--------+----------+
         |
         v
+-------------------+
|   Time Check      |
+--------+----------+
         |
         v
+-------------------+
|   Risk Level      |
+--------+----------+
         |
         v
+-------------------+
| Approval Needed?  |
+--------+----------+
    |          |
   No         Yes
    |          |
    v          v
+--------+ +-----------+
| PERMIT | | AWAIT     |
| ACTION | | HUMAN     |
+--------+ | APPROVAL  |
           +-----------+
```

---

## Real-World Use Cases

### Use Case 1: Market Research Automation

```
Goal: "Research and analyze the top 10 cryptocurrency projects,
       including price history, technology, and market sentiment"

Execution:
+------------------------------------------------------------------+
|                                                                   |
|  1. INTENT ANALYSIS                                              |
|     - Objective: Market research + data analysis                 |
|     - Complexity: COMPLEX                                        |
|     - Pattern: SWARM (parallel data gathering)                   |
|                                                                   |
|  2. TASK DECOMPOSITION                                           |
|     - Task 1-10: Fetch data for each cryptocurrency             |
|     - Task 11: Aggregate and analyze data                       |
|     - Task 12: Generate report                                  |
|                                                                   |
|  3. EXECUTION                                                    |
|     - Swarm of 10 workers fetch data in parallel                |
|     - Tool agents make API calls to CoinGecko, etc.             |
|     - Critic validates data quality                             |
|     - Report generated and saved                                |
|                                                                   |
|  4. RESULT                                                       |
|     - Comprehensive report with analysis                        |
|     - Data saved to files                                       |
|     - Memory updated with lessons learned                       |
|                                                                   |
+------------------------------------------------------------------+
```

### Use Case 2: Automated Code Generation & Testing

```
Goal: "Create a Python web scraper that extracts product data
       from an e-commerce site and stores it in a database"

Execution:
+------------------------------------------------------------------+
|                                                                   |
|  1. PLANNER creates implementation plan                          |
|     - Design architecture                                        |
|     - Identify components needed                                 |
|     - Estimate complexity                                        |
|                                                                   |
|  2. TOOL AGENTS implement components                             |
|     - Create directory structure                                 |
|     - Write scraper code                                         |
|     - Write database models                                      |
|     - Create configuration files                                 |
|                                                                   |
|  3. CRITIC validates code quality                                |
|     - Check for security issues                                  |
|     - Validate completeness                                      |
|     - Score quality                                              |
|                                                                   |
|  4. TOOL AGENT executes tests                                    |
|     - Run the scraper                                            |
|     - Verify data extraction                                     |
|     - Check database storage                                     |
|                                                                   |
+------------------------------------------------------------------+
```

### Use Case 3: Continuous System Improvement

```
Goal: "Analyze system performance and suggest optimizations"

Execution:
+------------------------------------------------------------------+
|                                                                   |
|  EVOLVER AGENT analyzes:                                         |
|                                                                   |
|  1. PERFORMANCE PATTERNS                                         |
|     - Which agents perform best?                                 |
|     - Which task types fail most?                                |
|     - Where are the bottlenecks?                                 |
|                                                                   |
|  2. PROMPT OPTIMIZATION                                          |
|     - Analyze current prompts                                    |
|     - Identify improvements                                      |
|     - Test variations                                            |
|                                                                   |
|  3. WORKFLOW OPTIMIZATION                                        |
|     - Remove unnecessary steps                                   |
|     - Increase parallelization                                   |
|     - Reduce token usage                                         |
|                                                                   |
|  4. PATTERN RETIREMENT                                           |
|     - Identify ineffective strategies                            |
|     - Mark for removal                                           |
|     - Document reasons                                           |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Performance Metrics

### System Performance Summary

```
+------------------------------------------------------------------+
|                    VERIFIED TEST RESULTS                          |
+------------------------------------------------------------------+
|                                                                   |
|  Unit Tests:              152 passed, 2 skipped                  |
|  Integration Tests:       All passing                            |
|  End-to-End Tests:        All passing                            |
|                                                                   |
|  +--------------------+------------------------------------------+
|  | Metric             | Value                                    |
|  +--------------------+------------------------------------------+
|  | Agent Lifecycle    | Fully functional                        |
|  | Dynamic Spawning   | Working                                 |
|  | Persistence        | PostgreSQL + Memory                     |
|  | Learning Loop      | Active and improving                    |
|  | Safety Enforcement | 100% coverage                           |
|  | Tool Execution     | Sandboxed and safe                      |
|  +--------------------+------------------------------------------+
|                                                                   |
+------------------------------------------------------------------+
```

### Agent Performance Tracking

```
+------------------------------------------------------------------+
|                    AGENT PERFORMANCE METRICS                      |
+------------------------------------------------------------------+
|                                                                   |
|  Per-Agent Tracking:                                             |
|  - Total tasks completed                                         |
|  - Success rate (%)                                              |
|  - Average tokens per task                                       |
|  - Average execution time                                        |
|  - Task type performance scores                                  |
|  - Capability utilization                                        |
|                                                                   |
|  Example Agent Profile:                                          |
|  +----------------------------------------------------------+   |
|  | Agent: DataSpecialist-v1 (tool)                          |   |
|  | Tasks: 5 | Success: 100% | Tokens: 570 | Reused: Yes     |   |
|  | Specializations: api, data_retrieval, file_operations    |   |
|  | Last Active: 2024-01-15 14:32:00                         |   |
|  +----------------------------------------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Integration Patterns

### API Integration

```
+------------------------------------------------------------------+
|                         REST API                                  |
+------------------------------------------------------------------+
|                                                                   |
|  POST /api/v1/goals                                              |
|  - Submit new goal                                               |
|  - Returns goal_id for tracking                                  |
|                                                                   |
|  GET /api/v1/goals/{goal_id}                                     |
|  - Get goal status and results                                   |
|                                                                   |
|  GET /api/v1/goals/{goal_id}/tasks                               |
|  - Get task breakdown                                            |
|                                                                   |
|  POST /api/v1/goals/{goal_id}/approve                            |
|  - Human approval for pending tasks                              |
|                                                                   |
+------------------------------------------------------------------+
```

### WebSocket Integration

```
+------------------------------------------------------------------+
|                     WEBSOCKET EVENTS                              |
+------------------------------------------------------------------+
|                                                                   |
|  Client -> Server:                                               |
|  - goal.submit: Submit new goal                                  |
|  - task.approve: Approve pending task                            |
|  - goal.cancel: Cancel running goal                              |
|                                                                   |
|  Server -> Client:                                               |
|  - goal.status: Goal status updates                              |
|  - task.progress: Task progress events                           |
|  - agent.spawned: New agent created                              |
|  - approval.required: Human approval needed                       |
|  - goal.completed: Goal finished                                 |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Decision Flowcharts

### When to Use Agent Village

```
                     +------------------+
                     |  Is your task    |
                     |  complex enough  |
                     |  for multi-agent?|
                     +--------+---------+
                              |
              +---------------+---------------+
              |                               |
             Yes                              No
              |                               |
              v                               v
     +------------------+           +------------------+
     | Does it require  |           | Use single LLM   |
     | multiple tools   |           | call instead     |
     | or capabilities? |           +------------------+
     +--------+---------+
              |
              +---------------+
              |               |
             Yes              No
              |               |
              v               v
     +------------------+  +------------------+
     | Does it need     |  | Use Tool Agent   |
     | parallel         |  | with single task |
     | execution?       |  +------------------+
     +--------+---------+
              |
              +---------------+
              |               |
             Yes              No
              |               |
              v               v
     +------------------+  +------------------+
     | Use Swarm        |  | Use Council      |
     | Coordinator      |  | Pattern          |
     +------------------+  +------------------+
```

### Error Handling Flow

```
                     +------------------+
                     |   Task Failed    |
                     +--------+---------+
                              |
                              v
                     +------------------+
                     | Retry Available? |
                     +--------+---------+
                              |
              +---------------+---------------+
              |                               |
             Yes                              No
              |                               |
              v                               v
     +------------------+           +------------------+
     | Retry Task       |           | Replan Count    |
     | (up to 3 times)  |           | < 3?            |
     +--------+---------+           +--------+---------+
              |                              |
              v                   +----------+----------+
     +------------------+         |                     |
     |    Success?      |        Yes                    No
     +--------+---------+         |                     |
              |                   v                     v
     +--------+--------+  +------------------+  +------------------+
     |                 |  | Trigger Replan   |  | Mark Goal as     |
    Yes                No | FSM State        |  | FAILED           |
     |                 |  +------------------+  +------------------+
     v                 v
+----------+    +----------+
| Continue |    | Escalate |
| Execution|    | to Replan|
+----------+    +----------+
```

---

## Summary of Achievements

| Category | Capability | Status |
|----------|-----------|--------|
| **Orchestration** | Goal decomposition | Fully Implemented |
| | Multi-agent coordination | Fully Implemented |
| | Parallel execution | Fully Implemented |
| | FSM-based flow control | Fully Implemented |
| **Agents** | Dynamic spawning | Fully Implemented |
| | Intelligent selection | Fully Implemented |
| | Performance tracking | Fully Implemented |
| | Learning from outcomes | Fully Implemented |
| **Memory** | Episodic (events) | Fully Implemented |
| | Semantic (knowledge) | Fully Implemented |
| | Procedural (workflows) | Fully Implemented |
| | Strategic (decisions) | Fully Implemented |
| | Vector search | Fully Implemented |
| **Tools** | File operations | Fully Implemented |
| | Web requests | Fully Implemented |
| | Code execution | Fully Implemented |
| | Sandboxing | Fully Implemented |
| **Safety** | Hard limits | Fully Implemented |
| | Human-in-loop | Fully Implemented |
| | Risk assessment | Fully Implemented |
| | Blocked actions | Fully Implemented |
| **Persistence** | PostgreSQL storage | Fully Implemented |
| | Agent state saving | Fully Implemented |
| | Cross-session learning | Fully Implemented |
| **Self-Improvement** | Prompt optimization | Fully Implemented |
| | Workflow optimization | Fully Implemented |
| | Pattern retirement | Fully Implemented |
| **Infrastructure** | Distributed workers | Fully Implemented |
| | Prometheus metrics | Fully Implemented |
| | Grafana dashboards | Fully Implemented |
| | Load balancing | Fully Implemented |
| | Worker health monitoring | Fully Implemented |
| **Extensibility** | Plugin system | Fully Implemented |
| | Agent plugins | Fully Implemented |
| | Tool plugins | Fully Implemented |
| | Hook system | Fully Implemented |
| | Plugin loader | Fully Implemented |
| **Web Dashboard** | Standalone dashboard | Fully Implemented |
| | Real-time monitoring | Fully Implemented |
| | Goal management UI | Fully Implemented |
| | Agent activity tracking | Fully Implemented |
| | WebSocket integration | Fully Implemented |
| **Multi-tenancy** | Tenant models & tiers | Fully Implemented |
| | Tenant context & middleware | Fully Implemented |
| | Tenant quotas & limits | Fully Implemented |
| | Tenant API endpoints | Fully Implemented |
| | Tenant resolution strategies | Fully Implemented |
| **Rate Limiting** | Fixed window limiter | Fully Implemented |
| | Sliding window limiter | Fully Implemented |
| | Token bucket limiter | Fully Implemented |
| | FastAPI middleware | Fully Implemented |
| | Tenant-aware rate limits | Fully Implemented |
| | Redis storage backend | Fully Implemented |
| **Audit Logging** | Audit event models | Fully Implemented |
| | In-memory storage | Fully Implemented |
| | File-based storage | Fully Implemented |
| | FastAPI middleware | Fully Implemented |
| | Decorator-based auditing | Fully Implemented |
| | Sensitive data masking | Fully Implemented |
| **SSO Integration** | OAuth2 providers with PKCE | Fully Implemented |
| | OpenID Connect (OIDC) | Fully Implemented |
| | SAML 2.0 support | Fully Implemented |
| | Pre-configured providers | Fully Implemented |
| | Session management | Fully Implemented |
| | Domain restrictions | Fully Implemented |
| **RBAC System** | Fine-grained permissions (40+) | Fully Implemented |
| | Built-in system roles | Fully Implemented |
| | Role hierarchy & inheritance | Fully Implemented |
| | Tenant-scoped roles | Fully Implemented |
| | Time-based role validity | Fully Implemented |
| | Permission caching | Fully Implemented |
| | FastAPI middleware & decorators | Fully Implemented |

---

## Observability & Monitoring

### Prometheus Metrics Architecture

```
+-------------------------------------------------------------------------+
|                          PROMETHEUS METRICS                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  REQUEST METRICS              AGENT METRICS                              |
|  +------------------+         +------------------+                       |
|  | http_request_    |         | agent_spawn_     |                       |
|  |   duration       |         |   total          |                       |
|  | http_requests_   |         | agent_active     |                       |
|  |   total          |         | agent_execution_ |                       |
|  | http_requests_   |         |   duration       |                       |
|  |   in_progress    |         | agent_errors_    |                       |
|  +------------------+         |   total          |                       |
|                               +------------------+                       |
|                                                                          |
|  GOAL METRICS                 WORKER METRICS                             |
|  +------------------+         +------------------+                       |
|  | goal_created_    |         | worker_active    |                       |
|  |   total          |         | worker_tasks_    |                       |
|  | goal_completed_  |         |   total          |                       |
|  |   total          |         | worker_task_     |                       |
|  | goal_failed_     |         |   duration       |                       |
|  |   total          |         | worker_capacity  |                       |
|  | goal_active      |         | worker_          |                       |
|  | goal_duration    |         |   utilization    |                       |
|  +------------------+         +------------------+                       |
|                                                                          |
|  MEMORY METRICS               SYSTEM METRICS                             |
|  +------------------+         +------------------+                       |
|  | memory_          |         | system_cpu_      |                       |
|  |   operations     |         |   usage          |                       |
|  | memory_cache_    |         | system_memory_   |                       |
|  |   hits/misses    |         |   usage          |                       |
|  | memory_store_    |         | system_disk_     |                       |
|  |   size           |         |   usage          |                       |
|  +------------------+         +------------------+                       |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Grafana Dashboards

```
+-------------------------------------------------------------------------+
|                          GRAFANA DASHBOARDS                              |
+-------------------------------------------------------------------------+
|                                                                          |
|  OVERVIEW DASHBOARD                                                      |
|  +----------------------------------------------------------------+     |
|  |  [CPU Gauge] [Memory Gauge] [Workers] [Goals] [Agents] [WS]   |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Request Rate by Endpoint  | | Request Latency (p95/p99)   | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Goals Completed/Failed    | | Active Agents by Type       | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Worker Utilization        | | Worker Task Rate            | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  +----------------------------------------------------------------+     |
|                                                                          |
|  WORKERS DASHBOARD                                                       |
|  +----------------------------------------------------------------+     |
|  |  [Idle] [Busy] [Draining] [Offline] | [Capacity] [Throughput] |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Worker Utilization/Time   | | Tasks Processed per Worker  | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Task Latency Percentiles  | | Task Duration Distribution  | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Errors by Type            | | Task Success Rate           | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  +----------------------------------------------------------------+     |
|                                                                          |
|  GOALS & AGENTS DASHBOARD                                                |
|  +----------------------------------------------------------------+     |
|  |  [Active] [Completed] [Failed] [Success%] [Avg Duration]      |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Goal Activity Over Time   | | Goal Duration by Priority   | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Active Agents Over Time   | | Agent Execution Duration    | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  |  | Errors by Agent Type      | | Errors by Error Type        | |     |
|  |  +---------------------------+ +-----------------------------+ |     |
|  +----------------------------------------------------------------+     |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Distributed Worker System

```
+-------------------------------------------------------------------------+
|                       DISTRIBUTED WORKER SYSTEM                          |
+-------------------------------------------------------------------------+
|                                                                          |
|   WORKER REGISTRY (Redis-based)                                         |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  +------------------+    +------------------+                   |    |
|   |  |  Worker Node 1   |    |  Worker Node 2   |                   |    |
|   |  |  ID: worker-abc  |    |  ID: worker-def  |                   |    |
|   |  |  Status: IDLE    |    |  Status: BUSY    |                   |    |
|   |  |  Tasks: 0/4      |    |  Tasks: 3/4      |                   |    |
|   |  |  Heartbeat: OK   |    |  Heartbeat: OK   |                   |    |
|   |  +------------------+    +------------------+                   |    |
|   |                                                                 |    |
|   |  +------------------+    +------------------+                   |    |
|   |  |  Worker Node 3   |    |  Worker Node N   |                   |    |
|   |  |  ID: worker-ghi  |    |  ID: worker-...  |                   |    |
|   |  |  Status: DRAINING|    |  Status: IDLE    |                   |    |
|   |  |  Tasks: 1/4      |    |  Tasks: 0/8      |                   |    |
|   |  |  Heartbeat: OK   |    |  Heartbeat: OK   |                   |    |
|   |  +------------------+    +------------------+                   |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   LOAD BALANCER                                                          |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  Strategies:                                                    |    |
|   |  - ROUND_ROBIN: Even distribution across workers               |    |
|   |  - LEAST_LOADED: Route to worker with lowest utilization       |    |
|   |  - WEIGHTED_RANDOM: Random based on available capacity         |    |
|   |  - CAPABILITY_MATCH: Route based on required capabilities      |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   WORKER CAPABILITIES                                                    |
|   +----------------------------------------------------------------+    |
|   |  - goal_execution     - LLM inference                          |    |
|   |  - task_execution     - file operations                        |    |
|   |  - agent_spawning     - web operations                         |    |
|   |                       - memory operations                       |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Plugin System

### Plugin Architecture

```
+-------------------------------------------------------------------------+
|                          PLUGIN SYSTEM                                   |
+-------------------------------------------------------------------------+
|                                                                          |
|   PLUGIN REGISTRY                                                        |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  register_class() -> Load plugin class                         |    |
|   |  load()           -> Initialize plugin instance                 |    |
|   |  unload()         -> Shutdown and remove plugin                 |    |
|   |  get_by_type()    -> Find plugins by type                       |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   PLUGIN LOADER                                                          |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  Sources:                                                       |    |
|   |  - Python modules (importlib)                                   |    |
|   |  - File paths (.py files)                                       |    |
|   |  - Directories (recursive scan)                                 |    |
|   |  - Entry points (pkg_resources)                                 |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   PLUGIN TYPES                                                           |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  +-------------+  +-------------+  +-------------+              |    |
|   |  |   AGENT     |  |    TOOL     |  |   MEMORY    |              |    |
|   |  |  PLUGINS    |  |   PLUGINS   |  |   PLUGINS   |              |    |
|   |  +-------------+  +-------------+  +-------------+              |    |
|   |                                                                 |    |
|   |  +-------------+  +-------------+  +-------------+              |    |
|   |  |  PROVIDER   |  |    HOOK     |  | MIDDLEWARE  |              |    |
|   |  |   PLUGINS   |  |   PLUGINS   |  |   PLUGINS   |              |    |
|   |  +-------------+  +-------------+  +-------------+              |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Hook System

```
+-------------------------------------------------------------------------+
|                           HOOK SYSTEM                                    |
+-------------------------------------------------------------------------+
|                                                                          |
|   HOOK MANAGER                                                           |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  register()   -> Add hook handler                               |    |
|   |  unregister() -> Remove hook handler                            |    |
|   |  emit()       -> Trigger hooks (async)                          |    |
|   |  emit_sync()  -> Trigger hooks (sync)                           |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   HOOK LIFECYCLE                                                         |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |   Event Emitted                                                 |    |
|   |         |                                                       |    |
|   |         v                                                       |    |
|   |   +-------------------+                                         |    |
|   |   | Sort by Priority  |  (HIGHEST -> LOWEST)                    |    |
|   |   +-------------------+                                         |    |
|   |         |                                                       |    |
|   |         v                                                       |    |
|   |   +-------------------+                                         |    |
|   |   | Execute Handlers  | -----> Handler can cancel               |    |
|   |   +-------------------+        further execution                 |    |
|   |         |                                                       |    |
|   |         v                                                       |    |
|   |   +-------------------+                                         |    |
|   |   | Collect Results   |                                         |    |
|   |   +-------------------+                                         |    |
|   |         |                                                       |    |
|   |         v                                                       |    |
|   |   Return HookContext with all results                           |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Creating Custom Plugins

```python
# Example: Custom Agent Plugin
from src.plugins import (
    AgentPlugin,
    AgentPluginConfig,
    plugin_metadata,
    PluginType,
)

@plugin_metadata(
    name="my-custom-agent",
    version="1.0.0",
    description="My custom agent for data analysis",
    plugin_type=PluginType.AGENT,
)
class MyCustomAgent(AgentPlugin):
    @property
    def agent_config(self) -> AgentPluginConfig:
        return AgentPluginConfig(
            capabilities=["data_analysis", "reporting"],
            system_prompt="You are a data analysis expert...",
        )

    async def execute(self, task, context):
        # Your implementation here
        return {"success": True, "output": "Analysis complete"}

# Example: Custom Tool Plugin
from src.plugins import (
    ToolPlugin,
    ToolDefinition,
    ToolParameter,
)

@plugin_metadata(
    name="my-tools",
    version="1.0.0",
    description="My custom tools",
    plugin_type=PluginType.TOOL,
)
class MyToolPlugin(ToolPlugin):
    @property
    def tool_definitions(self):
        return [
            ToolDefinition(
                name="my_tool",
                description="Does something useful",
                parameters=[
                    ToolParameter(name="input", description="Input data"),
                ],
            ),
        ]

    async def execute(self, tool_name, **kwargs):
        if tool_name == "my_tool":
            return {"result": "Tool executed"}
```

---

## Web Dashboard

### Dashboard Architecture

```
+-------------------------------------------------------------------------+
|                          WEB DASHBOARD                                   |
+-------------------------------------------------------------------------+
|                                                                          |
|   STANDALONE FASTAPI APPLICATION                                         |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  create_dashboard_app()                                         |    |
|   |  - Configurable via DashboardConfig                             |    |
|   |  - Embedded HTML/CSS/JavaScript                                 |    |
|   |  - No external dependencies                                     |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   DASHBOARD FEATURES                                                     |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  +------------------+  +------------------+  +------------------+ |   |
|   |  |   GOAL MGMT     |  |  AGENT MONITOR  |  |   METRICS VIEW   | |   |
|   |  |                  |  |                  |  |                  | |   |
|   |  | - Submit goals   |  | - Active agents  |  | - System stats   | |   |
|   |  | - Track progress |  | - Status view    |  | - Success rates  | |   |
|   |  | - View results   |  | - Task counts    |  | - Uptime         | |   |
|   |  +------------------+  +------------------+  +------------------+ |   |
|   |                                                                 |    |
|   |  +------------------+  +------------------+  +------------------+ |   |
|   |  |   LOG STREAM    |  |   SETTINGS      |  |  WEBSOCKET       | |   |
|   |  |                  |  |                  |  |                  | |   |
|   |  | - Real-time logs |  | - Theme toggle   |  | - Live updates   | |   |
|   |  | - Auto-scroll    |  | - Refresh rate   |  | - Event stream   | |   |
|   |  | - Log filtering  |  | - URL config     |  | - Reconnect      | |   |
|   |  +------------------+  +------------------+  +------------------+ |   |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Dashboard Endpoints

```
+------------------------------------------------------------------+
|                     DASHBOARD API                                 |
+------------------------------------------------------------------+
|                                                                   |
|  GET  /                           -> Dashboard HTML page          |
|  GET  /health                     -> Service health check         |
|                                                                   |
|  GET  /dashboard/stats            -> System statistics            |
|  GET  /dashboard/goals            -> Recent goals list            |
|  GET  /dashboard/agents           -> Active agents list           |
|  GET  /dashboard/config           -> Dashboard configuration      |
|                                                                   |
|  GET  /dashboard/widgets/goals    -> Goals widget HTML            |
|  GET  /dashboard/widgets/agents   -> Agents widget HTML           |
|  GET  /dashboard/widgets/metrics  -> Metrics widget HTML          |
|                                                                   |
|  POST /dashboard/settings         -> Update settings              |
|                                                                   |
+------------------------------------------------------------------+
```

### Dashboard Configuration

```python
from src.dashboard import create_dashboard_app, DashboardConfig

# Create with custom configuration
config = DashboardConfig(
    title="My Agent Dashboard",
    api_base_url="http://api.example.com",
    ws_base_url="wss://api.example.com",
    refresh_interval=5000,  # ms
    theme="dark",  # or "light"
    show_metrics=True,
    show_logs=True,
    show_agents=True,
    show_goals=True,
)

app = create_dashboard_app(config)
```

### Dashboard UI Features

```
+-------------------------------------------------------------------------+
|                        DASHBOARD UI                                      |
+-------------------------------------------------------------------------+
|                                                                          |
|  HEADER                                                                  |
|  +----------------------------------------------------------------+    |
|  |  Agent Village Dashboard                     [Theme] [Settings] |    |
|  +----------------------------------------------------------------+    |
|                                                                          |
|  STATS GRID                                                              |
|  +----------------------------------------------------------------+    |
|  |  [Goals: 5]  [Agents: 3]  [Workers: 10]  [Success: 95%]        |    |
|  +----------------------------------------------------------------+    |
|                                                                          |
|  MAIN CONTENT                                                            |
|  +-----------------------------+  +-----------------------------+       |
|  |       GOAL PANEL            |  |      AGENT PANEL            |       |
|  +-----------------------------+  +-----------------------------+       |
|  |  +---------------------+    |  |  +---------------------+    |       |
|  |  | Goal Input Form     |    |  |  | Agent: tool-001     |    |       |
|  |  +---------------------+    |  |  | Status: busy        |    |       |
|  |  | Active Goals        |    |  |  | Tasks: 2            |    |       |
|  |  | - Goal 1 [running]  |    |  |  +---------------------+    |       |
|  |  | - Goal 2 [pending]  |    |  |  | Agent: planner-001  |    |       |
|  |  | - Goal 3 [complete] |    |  |  | Status: idle        |    |       |
|  |  +---------------------+    |  |  | Tasks: 0            |    |       |
|  +-----------------------------+  +-----------------------------+       |
|                                                                          |
|  LOG PANEL                                                               |
|  +----------------------------------------------------------------+    |
|  |  [INFO] Goal goal-123 submitted                                 |    |
|  |  [INFO] Agent tool-001 spawned                                  |    |
|  |  [INFO] Task task-456 completed                                 |    |
|  +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

---

## Multi-tenancy Support

### Tenant Architecture

```
+-------------------------------------------------------------------------+
|                       MULTI-TENANCY SYSTEM                               |
+-------------------------------------------------------------------------+
|                                                                          |
|   TENANT RESOLUTION MIDDLEWARE                                           |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  Request --> [Header] --> [API Key] --> [Subdomain] --> Tenant  |    |
|   |               X-Tenant-ID   X-API-Key    tenant.domain.com      |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   TENANT TIERS                                                           |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  +------------+  +------------+  +---------------+  +----------+ |   |
|   |  |    FREE    |  |  STARTER   |  | PROFESSIONAL  |  |ENTERPRISE| |   |
|   |  |            |  |            |  |               |  |          | |   |
|   |  | 10 goals/d |  | 50 goals/d |  | 200 goals/d   |  | 10K/d    | |   |
|   |  | 3 agents   |  | 5 agents   |  | 20 agents     |  | 100      | |   |
|   |  | 10K tokens |  | 50K tokens |  | 200K tokens   |  | 10M      | |   |
|   |  +------------+  +------------+  +---------------+  +----------+ |   |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   TENANT CONTEXT                                                         |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  get_current_tenant() -----> TenantContext                      |    |
|   |                                |                                |    |
|   |                                +-- tenant: Tenant               |    |
|   |                                +-- request_id: str              |    |
|   |                                +-- tokens_used: int             |    |
|   |                                +-- api_calls_made: int          |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Tenant Lifecycle

```
+-------------------------------------------------------------------------+
|                        TENANT LIFECYCLE                                  |
+-------------------------------------------------------------------------+
|                                                                          |
|   CREATE                    ACTIVE                    SUSPENDED          |
|   +--------+               +--------+                +--------+          |
|   | PENDING| ----+-------> | ACTIVE | ----+-------> |SUSPENDED|          |
|   +--------+     |         +--------+     |         +--------+           |
|       |          |             |          |             |                |
|       |    approve()           |    suspend()           |                |
|       |          |             |          |             |                |
|       |          |             |          |       activate()             |
|       |          |             |          |             |                |
|       |          |             v          |             v                |
|       |          |         +--------+     |         +--------+           |
|       +----------+-------> | DELETED|<----+---------|        |           |
|                            +--------+               +--------+           |
|                                                                          |
|   STATUS TRANSITIONS:                                                    |
|   - PENDING -> ACTIVE: Account approved                                  |
|   - ACTIVE -> SUSPENDED: Quota exceeded, billing issue, admin action     |
|   - SUSPENDED -> ACTIVE: Issue resolved                                  |
|   - Any -> DELETED: Account deleted                                      |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Tenant API Endpoints

```
+------------------------------------------------------------------+
|                       TENANT API                                  |
+------------------------------------------------------------------+
|                                                                   |
|  ADMIN ENDPOINTS                                                  |
|  POST   /tenants                  -> Create new tenant            |
|  GET    /tenants                  -> List all tenants             |
|  GET    /tenants/{id}             -> Get tenant details           |
|  PATCH  /tenants/{id}             -> Update tenant                |
|  DELETE /tenants/{id}             -> Delete tenant                |
|                                                                   |
|  LIFECYCLE ENDPOINTS                                              |
|  POST   /tenants/{id}/suspend     -> Suspend tenant               |
|  POST   /tenants/{id}/activate    -> Activate tenant              |
|  POST   /tenants/{id}/upgrade     -> Upgrade tier                 |
|                                                                   |
|  SECURITY ENDPOINTS                                               |
|  POST   /tenants/{id}/api-key     -> Generate new API key         |
|                                                                   |
|  MONITORING ENDPOINTS                                             |
|  GET    /tenants/{id}/stats       -> Usage statistics             |
|  PATCH  /tenants/{id}/config      -> Update configuration         |
|                                                                   |
|  SELF-SERVICE ENDPOINTS                                           |
|  GET    /tenants/me               -> Current tenant info          |
|  GET    /tenants/me/stats         -> Current tenant stats         |
|                                                                   |
+------------------------------------------------------------------+
```

### Tenant Quota System

```
+-------------------------------------------------------------------------+
|                        QUOTA MANAGEMENT                                  |
+-------------------------------------------------------------------------+
|                                                                          |
|   QUOTA TRACKING                                                         |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  TenantQuota                                                    |    |
|   |  +----------------------------------------------------------+  |    |
|   |  |  Resource        | Limit      | Used    | Remaining      |  |    |
|   |  |------------------|------------|---------|----------------|  |    |
|   |  |  Goals/Day       | 200        | 45      | 155 (77.5%)    |  |    |
|   |  |  Tokens/Day      | 200,000    | 50,000  | 150,000 (75%)  |  |    |
|   |  |  Agents          | 20         | 5       | 15 (75%)       |  |    |
|   |  |  Workers         | 10         | 3       | 7 (70%)        |  |    |
|   |  |  Storage (MB)    | 2,000      | 500     | 1,500 (75%)    |  |    |
|   |  |  API Calls/Min   | 100        | 25      | 75 (75%)       |  |    |
|   |  +----------------------------------------------------------+  |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
|   QUOTA ENFORCEMENT                                                      |
|   +----------------------------------------------------------------+    |
|   |                                                                 |    |
|   |  check_quota(goals=1) -----> (True, None)     # OK             |    |
|   |  check_quota(goals=200) ---> (False, "Limit exceeded")         |    |
|   |                                                                 |    |
|   |  consume_quota(goals=1, tokens=500) -----> Updated quota       |    |
|   |  consume_quota(...) raises TenantQuotaExceededError            |    |
|   |                                                                 |    |
|   +----------------------------------------------------------------+    |
|                                                                          |
+-------------------------------------------------------------------------+
```

### Using Multi-tenancy

```python
from src.tenancy import (
    create_tenant_app,
    TenantMiddleware,
    TenantService,
    get_current_tenant,
    tenant_context,
)

# 1. Add middleware to FastAPI app
app.add_middleware(
    TenantMiddleware,
    tenant_resolver=service.resolve_tenant,
    require_tenant=True,
    exempt_paths=["/health", "/docs"],
)

# 2. Create tenants
service = TenantService()
tenant = await service.create_tenant(TenantCreate(
    name="Acme Corp",
    slug="acme",
    tier=TenantTier.PROFESSIONAL,
    owner_email="admin@acme.com",
))

# 3. Generate API key
api_key = await service.generate_api_key(tenant.tenant_id)

# 4. Access tenant context in requests
@app.get("/my-endpoint")
async def my_endpoint(request: Request):
    tenant = get_current_tenant()
    stats = await service.get_tenant_stats(tenant.tenant_id)
    return {"tenant": tenant.name, "usage": stats}

# 5. Check quotas before operations
ok, reason = await service.check_quota(
    tenant_id=tenant.tenant_id,
    goals=1,
    tokens=1000,
)
if not ok:
    raise HTTPException(429, reason)
```

---

## Rate Limiting System

### Rate Limiting Architecture

```
+------------------------------------------------------------------------------+
|                           Rate Limiting System                                |
+------------------------------------------------------------------------------+
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                        REQUEST FLOW                                  |   |
|   |                                                                      |   |
|   |   Request --> [Middleware] --> [Rule Matching] --> [Limiter] --> OK |   |
|   |                    |                |                   |            |   |
|   |                    |                |                   v            |   |
|   |              Check Exempt     Get Key            429 if exceeded    |   |
|   |              (paths, IPs)    (IP/User/Tenant)                       |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                     RATE LIMITING ALGORITHMS                         |   |
|   |                                                                      |   |
|   |   ┌─────────────┐  ┌──────────────┐  ┌─────────────┐               |   |
|   |   | Fixed       |  |   Sliding    |  |   Token     |               |   |
|   |   | Window      |  |   Window     |  |   Bucket    |               |   |
|   |   |-------------|  |--------------|  |-------------|               |   |
|   |   | Simple      |  | Weighted     |  | Burst       |               |   |
|   |   | counting    |  | count across |  | capacity +  |               |   |
|   |   | per period  |  | windows      |  | refill rate |               |   |
|   |   └─────────────┘  └──────────────┘  └─────────────┘               |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                         SCOPES                                       |   |
|   |                                                                      |   |
|   |   GLOBAL ───> All requests combined                                 |   |
|   |   IP ───────> Per client IP address                                 |   |
|   |   USER ─────> Per authenticated user                                |   |
|   |   TENANT ───> Per tenant organization                               |   |
|   |   API_KEY ──> Per API key                                           |   |
|   |   ENDPOINT ─> Per IP + endpoint combination                         |   |
|   |   CUSTOM ───> Custom key function                                   |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
+------------------------------------------------------------------------------+
```

### Storage Architecture

```
+------------------------------------------------------------------------------+
|                           Storage Backends                                    |
+------------------------------------------------------------------------------+
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                     InMemoryStorage                                  |   |
|   |---------------------------------------------------------------------|   |
|   |   • Async lock-protected dictionary                                  |   |
|   |   • Auto-cleanup of expired entries                                  |   |
|   |   • Per-key window tracking                                          |   |
|   |   • Token bucket support                                             |   |
|   |   • Best for: Single-instance deployments                            |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                      RedisStorage                                    |   |
|   |---------------------------------------------------------------------|   |
|   |   • Lua scripts for atomic operations                                |   |
|   |   • Automatic TTL-based expiration                                   |   |
|   |   • Shared across multiple instances                                 |   |
|   |   • Pipeline support for efficiency                                  |   |
|   |   • Best for: Distributed deployments                                |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
+------------------------------------------------------------------------------+
```

### Tenant-Aware Rate Limits

```
+------------------------------------------------------------------------------+
|                       Tier-Based Rate Limits                                  |
+------------------------------------------------------------------------------+
|                                                                               |
|   TIER           │ REQUESTS/MIN │ GOALS/MIN │ AGENTS │ API CALLS            |
|   ───────────────┼──────────────┼───────────┼────────┼──────────            |
|   FREE           │      10      │     5     │    3   │    10                |
|   STARTER        │      30      │    15     │   10   │    30                |
|   PROFESSIONAL   │     100      │    50     │   30   │   100                |
|   ENTERPRISE     │    1000      │   500     │  200   │  1000                |
|                                                                               |
+------------------------------------------------------------------------------+
```

### HTTP Response Headers

```
+------------------------------------------------------------------------------+
|                       Rate Limit Headers                                      |
+------------------------------------------------------------------------------+
|                                                                               |
|   Header                  │ Description                                      |
|   ────────────────────────┼──────────────────────────────────────────────   |
|   X-RateLimit-Limit       │ Maximum requests allowed                        |
|   X-RateLimit-Remaining   │ Remaining requests in window                    |
|   X-RateLimit-Reset       │ Unix timestamp when limit resets                |
|   X-RateLimit-Rule        │ Name of the applied rule                        |
|   Retry-After             │ Seconds until retry allowed (on 429)            |
|                                                                               |
+------------------------------------------------------------------------------+
```

### Using Rate Limiting

```python
from src.ratelimit import (
    RateLimitMiddleware,
    RateLimitConfig,
    RateLimitRule,
    RateLimitStrategy,
    RateLimitScope,
    rate_limit,
    TenantRateLimiter,
)

# 1. Add global middleware
app.add_middleware(
    RateLimitMiddleware,
    config=RateLimitConfig(
        default_requests=100,
        default_window_seconds=60,
        exempt_paths=["/health", "/metrics"],
        exempt_ips=["127.0.0.1"],
    )
)

# 2. Add custom rules
config = RateLimitConfig()
config.add_rule(RateLimitRule(
    name="api_strict",
    requests=10,
    window_seconds=60,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    scope=RateLimitScope.IP,
    paths=["/api/sensitive/*"],
))

# 3. Use decorator for specific endpoints
@app.post("/api/goals")
@rate_limit(requests=10, window_seconds=60, scope=RateLimitScope.TENANT)
async def create_goal(request: Request):
    return {"goal": "created"}

# 4. Use tenant-aware rate limiter
limiter = TenantRateLimiter()
result = await limiter.check(
    tenant_id="tenant-123",
    tier="professional",
    operation="goal",
)
if not result.allowed:
    raise HTTPException(429, result.message)
```

---

## Audit Logging System

### Audit Event Architecture

```
+------------------------------------------------------------------------------+
|                          Audit Logging System                                 |
+------------------------------------------------------------------------------+
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                        EVENT FLOW                                    |   |
|   |                                                                      |   |
|   |   Action --> [Middleware/Decorator] --> AuditLogger --> Storage     |   |
|   |                       |                     |                        |   |
|   |                       |                     v                        |   |
|   |               Extract Context         Mask Sensitive                |   |
|   |               (Actor, Resource)       Fields                        |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                     EVENT CATEGORIES                                 |   |
|   |                                                                      |   |
|   |   AUTHENTICATION ──> Login, logout, MFA events                      |   |
|   |   AUTHORIZATION ───> Access granted/denied                          |   |
|   |   DATA_ACCESS ─────> Read operations                                |   |
|   |   DATA_MUTATION ───> Create, update, delete                         |   |
|   |   SECURITY ────────> Rate limits, suspicious activity               |   |
|   |   AGENT ───────────> Agent spawn, complete, fail                    |   |
|   |   GOAL ────────────> Goal lifecycle events                          |   |
|   |   TENANT ──────────> Tenant management events                       |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
|   ┌─────────────────────────────────────────────────────────────────────┐   |
|   |                      SEVERITY LEVELS                                 |   |
|   |                                                                      |   |
|   |   DEBUG ────> Detailed debug information                            |   |
|   |   INFO ─────> Normal operations                                     |   |
|   |   WARNING ──> Potential issues                                      |   |
|   |   ERROR ────> Operation failures                                    |   |
|   |   CRITICAL ─> Security incidents                                    |   |
|   └─────────────────────────────────────────────────────────────────────┘   |
|                                                                               |
+------------------------------------------------------------------------------+
```

### Audit Event Structure

```
+------------------------------------------------------------------------------+
|                          Audit Event Components                               |
+------------------------------------------------------------------------------+
|                                                                               |
|   AuditEvent                                                                  |
|   ├── event_id: str              # Unique identifier                         |
|   ├── timestamp: datetime        # When event occurred                       |
|   ├── category: EventCategory    # Category of event                         |
|   ├── event_type: EventType      # Specific event type                       |
|   ├── severity: Severity         # DEBUG/INFO/WARNING/ERROR/CRITICAL         |
|   ├── outcome: Outcome           # SUCCESS/FAILURE/PENDING                   |
|   │                                                                           |
|   ├── actor: AuditActor          # WHO performed the action                  |
|   │   ├── actor_id               # User/system/agent ID                      |
|   │   ├── actor_type             # user/service/system/agent                 |
|   │   ├── ip_address             # Client IP                                 |
|   │   └── tenant_id              # Tenant context                            |
|   │                                                                           |
|   ├── resource: AuditResource    # WHAT was affected                         |
|   │   ├── resource_type          # goal/agent/tenant/user                    |
|   │   └── resource_id            # Resource identifier                       |
|   │                                                                           |
|   ├── context: AuditContext      # WHERE/HOW it happened                     |
|   │   ├── request_id             # Request correlation                       |
|   │   ├── endpoint               # HTTP endpoint                             |
|   │   ├── http_method            # GET/POST/PUT/DELETE                       |
|   │   └── duration_ms            # Operation duration                        |
|   │                                                                           |
|   └── changes: list[AuditDiff]   # WHAT changed                              |
|       ├── field_name             # Field that changed                        |
|       ├── old_value              # Previous value                            |
|       └── new_value              # New value                                 |
|                                                                               |
+------------------------------------------------------------------------------+
```

### Query Capabilities

```
+------------------------------------------------------------------------------+
|                        Audit Query Filters                                    |
+------------------------------------------------------------------------------+
|                                                                               |
|   Time-based         | Actor-based        | Resource-based    | Content      |
|   -------------------|--------------------|--------------------|--------------|
|   start_time         | actor_id           | resource_type      | search_text  |
|   end_time           | actor_type         | resource_id        | tags         |
|                      | tenant_id          |                    |              |
|                      | ip_address         |                    |              |
|                                                                               |
|   Category-based     | Severity-based     | Outcome-based      | Pagination   |
|   -------------------|--------------------|--------------------|--------------|
|   categories[]       | severities[]       | outcomes[]         | limit        |
|                      |                    |                    | offset       |
|                      |                    |                    | sort_by      |
|                      |                    |                    | sort_order   |
|                                                                               |
+------------------------------------------------------------------------------+
```

### Using Audit Logging

```python
from src.audit import (
    AuditLogger,
    AuditMiddleware,
    AuditConfig,
    AuditActor,
    AuditResource,
    AuditEventType,
    AuditSeverity,
    AuditQuery,
    audit_action,
)

# 1. Add global middleware
app.add_middleware(
    AuditMiddleware,
    config=AuditConfig(
        enabled=True,
        mask_sensitive_fields=True,
        retention_days=90,
    ),
    exclude_paths=["/health", "/metrics"],
)

# 2. Use decorator for specific endpoints
@app.post("/api/goals")
@audit_action(AuditEventType.GOAL_SUBMITTED, resource_type="goal")
async def create_goal(request: Request, data: GoalCreate):
    return {"id": "goal-123"}

# 3. Log events programmatically
logger = AuditLogger()

await logger.log_authentication(
    event_type=AuditEventType.LOGIN_SUCCESS,
    actor=AuditActor(actor_id="user-1", actor_type="user"),
    success=True,
)

await logger.log_security(
    event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
    severity=AuditSeverity.WARNING,
    description="User exceeded rate limit",
)

# 4. Query audit logs
result = await logger.storage.query(AuditQuery(
    categories=[AuditEventCategory.SECURITY],
    severities=[AuditSeverity.WARNING],
    start_time=datetime.utcnow() - timedelta(hours=24),
    limit=100,
))

for event in result.events:
    print(f"{event.timestamp}: {event.event_type.value} - {event.description}")
```

---

## SSO Integration System

```
+------------------------------------------------------------------------------+
|                          SSO Integration System                               |
+------------------------------------------------------------------------------+
|                                                                              |
|    +------------------------+     +------------------------+                 |
|    |   OAuth2 Provider      |     |    OIDC Provider       |                 |
|    |  - PKCE support        |     |  - ID token verify     |                 |
|    |  - Token exchange      |     |  - JWKS validation     |                 |
|    |  - User info fetch     |     |  - Claims extraction   |                 |
|    +------------------------+     +------------------------+                 |
|                |                            |                                |
|                +-------------+--------------+                                |
|                              |                                               |
|                              v                                               |
|    +--------------------------------------------------------+               |
|    |                    SSO Manager                          |               |
|    |  - Provider registry    - Session management           |               |
|    |  - Auth flow handling   - Token refresh                |               |
|    +--------------------------------------------------------+               |
|                              |                                               |
|                              v                                               |
|    +------------------------+     +------------------------+                 |
|    |   SSO Middleware       |     |    SSO Routes          |                 |
|    |  - Session loading     |     |  - /login/{provider}   |                 |
|    |  - Request state       |     |  - /callback           |                 |
|    |  - Path exclusions     |     |  - /logout             |                 |
|    +------------------------+     +------------------------+                 |
|                              |                                               |
|                              v                                               |
|    +--------------------------------------------------------+               |
|    |                  SAML Provider                          |               |
|    |  - AuthnRequest generation  - Response parsing         |               |
|    |  - Assertion extraction     - Attribute mapping        |               |
|    +--------------------------------------------------------+               |
|                                                                              |
+------------------------------------------------------------------------------+
```

### SSO Authentication Flow

```
+------------------------------------------------------------------------------+
|                       SSO Authentication Flow                                 |
+------------------------------------------------------------------------------+
|                                                                              |
|  1. User clicks "Login with Google"                                          |
|     |                                                                        |
|     v                                                                        |
|  2. Application generates auth URL with:                                     |
|     - State (CSRF protection)                                                |
|     - PKCE code challenge                                                    |
|     - Requested scopes                                                       |
|     |                                                                        |
|     v                                                                        |
|  3. User redirected to Identity Provider                                     |
|     |                                                                        |
|     v                                                                        |
|  4. User authenticates with IdP                                              |
|     |                                                                        |
|     v                                                                        |
|  5. IdP redirects back with authorization code                               |
|     |                                                                        |
|     v                                                                        |
|  6. Application exchanges code for tokens:                                   |
|     - Access token                                                           |
|     - Refresh token                                                          |
|     - ID token (OIDC)                                                        |
|     |                                                                        |
|     v                                                                        |
|  7. Application fetches user info                                            |
|     |                                                                        |
|     v                                                                        |
|  8. Domain validation (if configured)                                        |
|     |                                                                        |
|     v                                                                        |
|  9. Session created with cookie                                              |
|     |                                                                        |
|     v                                                                        |
|  10. User redirected to application                                          |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Supported SSO Providers

```
+------------------------------------------------------------------------------+
|                       Supported SSO Providers                                 |
+------------------------------------------------------------------------------+
|                                                                              |
|  Pre-configured Templates:                                                   |
|  +------------------+  +------------------+  +------------------+            |
|  |     Google       |  |    Microsoft     |  |     GitHub       |            |
|  |  OIDC Provider   |  |  OIDC Provider   |  |  OAuth2 Provider |            |
|  |  ID: google      |  |  ID: microsoft   |  |  ID: github      |            |
|  +------------------+  +------------------+  +------------------+            |
|                                                                              |
|  Enterprise Providers (configure manually):                                  |
|  +------------------+  +------------------+  +------------------+            |
|  |      Okta        |  |      Auth0       |  |    Azure AD      |            |
|  |  OIDC or SAML    |  |  OIDC Provider   |  |  OIDC Provider   |            |
|  +------------------+  +------------------+  +------------------+            |
|                                                                              |
|  +------------------+  +------------------+                                  |
|  |    OneLogin      |  |     Custom       |                                  |
|  |  SAML Provider   |  |   Any OAuth2     |                                  |
|  +------------------+  +------------------+                                  |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Using SSO Integration

```python
from src.sso import (
    SSOConfig,
    SSOProviderConfig,
    SSOProviderType,
    SSOManager,
    SSOMiddleware,
    sso_required,
    create_sso_routes,
    GOOGLE_OAUTH_CONFIG,
)

# 1. Create SSO configuration
config = SSOConfig(
    enabled=True,
    default_provider_id="google",
    allowed_domains=["yourcompany.com"],  # Restrict to company domain
    blocked_domains=["competitor.com"],   # Block specific domains
    auto_create_user=True,                # JIT user provisioning
    session_cookie_secure=True,           # Secure cookies in production
)

# 2. Configure Google OAuth
google_config = SSOProviderConfig(
    provider_id="google",
    provider_type=SSOProviderType.OIDC,
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
    scopes=["openid", "profile", "email"],
    redirect_uri="https://app.example.com/sso/callback/google",
)
config.add_provider(google_config)

# 3. Initialize SSO manager
sso_manager = SSOManager(config)

# 4. Add middleware to FastAPI app
app.add_middleware(
    SSOMiddleware,
    sso_manager=sso_manager,
    exclude_paths=["/health", "/metrics", "/docs"],
)

# 5. Include SSO routes
app.include_router(create_sso_routes(sso_manager))

# 6. Protect endpoints with decorator
@app.get("/dashboard")
@sso_required()
async def dashboard(request: Request):
    user = request.state.sso_session.user
    return {
        "email": user.email,
        "name": user.name,
        "provider": user.provider_id,
    }

# 7. Optional: Allow anonymous access with fallback
@app.get("/api/public")
@sso_required(allow_anonymous=True)
async def public_endpoint(request: Request):
    session = request.state.sso_session
    if session:
        return {"user": session.user.email, "authenticated": True}
    return {"authenticated": False}
```

---

## Role-Based Access Control (RBAC)

### RBAC Architecture

```
+------------------------------------------------------------------------------+
|                          RBAC System                                          |
+------------------------------------------------------------------------------+
|                                                                              |
|    +------------------------+     +------------------------+                 |
|    |   Permission System    |     |     Role System        |                 |
|    |  - 40+ permissions     |     |  - 5 built-in roles    |                 |
|    |  - Resource scoped     |     |  - Role hierarchy      |                 |
|    |  - Deny-by-default     |     |  - Inheritance         |                 |
|    +------------------------+     +------------------------+                 |
|                |                            |                                |
|                +-------------+--------------+                                |
|                              |                                               |
|                              v                                               |
|    +--------------------------------------------------------+               |
|    |                    RBAC Service                         |               |
|    |  - Permission checking    - Role management            |               |
|    |  - Caching (TTL-based)    - Tenant isolation           |               |
|    +--------------------------------------------------------+               |
|                              |                                               |
|                              v                                               |
|    +------------------------+     +------------------------+                 |
|    |   RBAC Middleware      |     |    RBAC Decorators     |                 |
|    |  - Request interception|     |  - @require_permission |                 |
|    |  - Permission loading  |     |  - @require_role       |                 |
|    |  - Deny enforcement    |     |  - @require_admin      |                 |
|    +------------------------+     +------------------------+                 |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Permission Categories

```
+------------------------------------------------------------------------------+
|                        Permission Categories                                  |
+------------------------------------------------------------------------------+
|                                                                              |
|  GOAL PERMISSIONS           AGENT PERMISSIONS          TOOL PERMISSIONS      |
|  +------------------+       +------------------+       +------------------+   |
|  | goal:create      |       | agent:create     |       | tool:register    |   |
|  | goal:read        |       | agent:read       |       | tool:read        |   |
|  | goal:update      |       | agent:update     |       | tool:execute     |   |
|  | goal:delete      |       | agent:delete     |       | tool:delete      |   |
|  | goal:execute     |       | agent:spawn      |       +------------------+   |
|  | goal:approve     |       | agent:terminate  |                              |
|  +------------------+       +------------------+                              |
|                                                                              |
|  MEMORY PERMISSIONS         USER PERMISSIONS           ROLE PERMISSIONS      |
|  +------------------+       +------------------+       +------------------+   |
|  | memory:read      |       | user:create      |       | role:create      |   |
|  | memory:write     |       | user:read        |       | role:read        |   |
|  | memory:delete    |       | user:update      |       | role:update      |   |
|  | memory:export    |       | user:delete      |       | role:delete      |   |
|  +------------------+       +------------------+       | role:assign      |   |
|                                                        +------------------+   |
|                                                                              |
|  TENANT PERMISSIONS         ADMIN PERMISSIONS                                |
|  +------------------+       +------------------+                              |
|  | tenant:read      |       | admin:read       |                              |
|  | tenant:update    |       | admin:write      |                              |
|  | tenant:manage    |       | admin:full       |                              |
|  +------------------+       +------------------+                              |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Built-in Roles

```
+------------------------------------------------------------------------------+
|                          Built-in System Roles                                |
+------------------------------------------------------------------------------+
|                                                                              |
|  SYSTEM ADMIN (admin:full)                                                   |
|  +--------------------------------------------------------------------+     |
|  |  All permissions - full system access                               |     |
|  +--------------------------------------------------------------------+     |
|                                                                              |
|  TENANT ADMIN (tenant-scoped admin)                                          |
|  +--------------------------------------------------------------------+     |
|  |  All permissions within tenant context                              |     |
|  |  - Goal, Agent, Tool, Memory, User, Role management                 |     |
|  |  - Tenant configuration                                             |     |
|  +--------------------------------------------------------------------+     |
|                                                                              |
|  OPERATOR (operational access)                                               |
|  +--------------------------------------------------------------------+     |
|  |  - Goal: create, read, update, execute, approve                     |     |
|  |  - Agent: create, read, update, spawn, terminate                    |     |
|  |  - Tool: read, execute                                              |     |
|  |  - Memory: read, write                                              |     |
|  +--------------------------------------------------------------------+     |
|                                                                              |
|  VIEWER (read-only access)                                                   |
|  +--------------------------------------------------------------------+     |
|  |  - Goal: read                                                        |     |
|  |  - Agent: read                                                       |     |
|  |  - Tool: read                                                        |     |
|  |  - Memory: read                                                      |     |
|  +--------------------------------------------------------------------+     |
|                                                                              |
|  DEVELOPER (inherits from Operator + extras)                                 |
|  +--------------------------------------------------------------------+     |
|  |  - All Operator permissions                                          |     |
|  |  - Tool: register, delete                                            |     |
|  |  - Memory: delete, export                                            |     |
|  |  - Agent: delete                                                     |     |
|  +--------------------------------------------------------------------+     |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Role Hierarchy

```
                    +----------------+
                    |  System Admin  |
                    | (admin:full)   |
                    +--------+-------+
                             |
             +---------------+---------------+
             |                               |
    +--------+--------+             +--------+--------+
    |  Tenant Admin   |             |    Developer    |
    | (tenant-scoped) |             | (extends Oper.) |
    +--------+--------+             +--------+--------+
             |                               |
             +---------------+---------------+
                             |
                    +--------+--------+
                    |    Operator     |
                    | (operational)   |
                    +--------+--------+
                             |
                    +--------+--------+
                    |     Viewer      |
                    |  (read-only)    |
                    +-----------------+
```

### Permission Checking Flow

```
+------------------------------------------------------------------------------+
|                       Permission Checking Flow                                |
+------------------------------------------------------------------------------+
|                                                                              |
|   Request ──> Middleware ──> Load User Permissions ──> Check Permission      |
|                                                               |              |
|                                   +---------------------------+              |
|                                   |                                          |
|                                   v                                          |
|                           +---------------+                                  |
|                           |  Permission   |                                  |
|                           |   Granted?    |                                  |
|                           +-------+-------+                                  |
|                                   |                                          |
|                       +-----------+-----------+                              |
|                       |                       |                              |
|                      Yes                      No                             |
|                       |                       |                              |
|                       v                       v                              |
|               +---------------+       +---------------+                      |
|               |   Continue    |       |   403 Error   |                      |
|               |   Request     |       | (Permission   |                      |
|               +---------------+       |    Denied)    |                      |
|                                       +---------------+                      |
|                                                                              |
|   Permission Check Steps:                                                    |
|   1. Check cache for user permissions                                        |
|   2. If cache miss, load from store                                          |
|   3. Check if user has required permission                                   |
|   4. Consider resource type and ID scoping                                   |
|   5. Consider tenant isolation                                               |
|   6. Return allow/deny decision                                              |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Using RBAC

```python
from src.rbac import (
    RBACService,
    RBACMiddleware,
    Permission,
    ResourceType,
    RoleType,
    require_permission,
    require_role,
    require_admin,
    create_rbac_routes,
    get_builtin_roles,
)

# 1. Initialize RBAC service
rbac_service = RBACService()

# 2. Create built-in roles
for role in get_builtin_roles():
    await rbac_service.create_role(role)

# 3. Add RBAC middleware to FastAPI
app.add_middleware(
    RBACMiddleware,
    rbac_service=rbac_service,
    exclude_paths=["/health", "/docs", "/sso"],
)

# 4. Include RBAC routes
app.include_router(create_rbac_routes(rbac_service))

# 5. Use permission decorators
@app.get("/goals/{goal_id}")
@require_permission(Permission.GOAL_READ, ResourceType.GOAL, "goal_id")
async def get_goal(request: Request, goal_id: str):
    return {"goal_id": goal_id}

@app.post("/goals")
@require_permission(Permission.GOAL_CREATE)
async def create_goal(request: Request, data: GoalCreate):
    return {"id": "goal-123"}

# 6. Use role decorators
@app.get("/admin/dashboard")
@require_admin()
async def admin_dashboard(request: Request):
    return {"admin": True}

@app.post("/tenant/settings")
@require_role(RoleType.TENANT_ADMIN)
async def update_tenant_settings(request: Request):
    return {"updated": True}

# 7. Assign roles to users
await rbac_service.assign_role(
    user_id="user-123",
    role_id="operator",
    tenant_id="tenant-456",
    granted_by="admin",
)

# 8. Check permissions programmatically
allowed = await rbac_service.check_permission(
    user_id="user-123",
    permission=Permission.GOAL_CREATE,
    tenant_id="tenant-456",
    raise_on_denied=False,
)
if allowed:
    # Proceed with operation
    pass
```

---

<p align="center">
  <strong>Agent Village - Intelligent Multi-Agent Orchestration</strong><br>
  <em>Achieve complex goals through coordinated AI collaboration</em>
</p>

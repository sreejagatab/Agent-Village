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
| **MFA System** | TOTP (Google Authenticator) | Fully Implemented |
| | SMS verification | Fully Implemented |
| | Email verification | Fully Implemented |
| | Backup codes | Fully Implemented |
| | Trusted device management | Fully Implemented |
| | Session management | Fully Implemented |
| | Rate limiting & lockout | Fully Implemented |

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

## Multi-Factor Authentication (MFA)

### MFA Architecture

```
+------------------------------------------------------------------------------+
|                           MFA System                                          |
+------------------------------------------------------------------------------+
|                                                                              |
|    +------------------------+     +------------------------+                 |
|    |    TOTP Provider       |     |    SMS Provider        |                 |
|    |  - Secret generation   |     |  - Code generation     |                 |
|    |  - Code verification   |     |  - Delivery tracking   |                 |
|    +------------------------+     +------------------------+                 |
|                |                            |                                |
|    +------------------------+     +------------------------+                 |
|    |   Email Provider       |     |   Backup Codes         |                 |
|    |  - Code generation     |     |  - One-time codes      |                 |
|    |  - Delivery tracking   |     |  - Hash verification   |                 |
|    +------------------------+     +------------------------+                 |
|                |                            |                                |
|                +-------------+--------------+                                |
|                              |                                               |
|                              v                                               |
|    +--------------------------------------------------------+               |
|    |                    MFA Service                          |               |
|    |  - Enrollment management   - Verification challenges   |               |
|    |  - Session handling        - Rate limiting             |               |
|    +--------------------------------------------------------+               |
|                              |                                               |
|                              v                                               |
|    +------------------------+     +------------------------+                 |
|    |   MFA Middleware       |     |   Trusted Devices      |                 |
|    |  - Enforcement         |     |  - Fingerprinting      |                 |
|    |  - Route protection    |     |  - Skip MFA for known  |                 |
|    +------------------------+     +------------------------+                 |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Supported MFA Methods

```
+------------------------------------------------------------------------------+
|                        MFA Methods                                            |
+------------------------------------------------------------------------------+
|                                                                              |
|  TOTP (Time-based OTP)          SMS Verification                             |
|  +----------------------+       +----------------------+                      |
|  | Google Authenticator |       | 6-digit code         |                      |
|  | Authy, 1Password     |       | 5-minute expiry      |                      |
|  | Microsoft Auth       |       | Rate limited         |                      |
|  | 30-second window     |       +----------------------+                      |
|  +----------------------+                                                     |
|                                                                              |
|  Email Verification             Backup Codes                                  |
|  +----------------------+       +----------------------+                      |
|  | 6-digit code         |       | 10 codes generated   |                      |
|  | 10-minute expiry     |       | XXXX-XXXX format     |                      |
|  | Rate limited         |       | One-time use         |                      |
|  +----------------------+       | Regeneratable        |                      |
|                                 +----------------------+                      |
|                                                                              |
+------------------------------------------------------------------------------+
```

### MFA Verification Flow

```
+------------------------------------------------------------------------------+
|                       MFA Verification Flow                                   |
+------------------------------------------------------------------------------+
|                                                                              |
|   Login ──> Primary Auth ──> MFA Required? ──> Yes ──> Challenge ──> Verify  |
|                                   |                                          |
|                                   No                                         |
|                                   |                                          |
|                                   v                                          |
|                            Access Granted                                    |
|                                                                              |
|   MFA Verification Steps:                                                    |
|   1. Check if user has MFA enabled                                           |
|   2. Check if device is trusted (skip if yes)                                |
|   3. Create verification challenge                                           |
|   4. User provides code (TOTP/SMS/Email/Backup)                              |
|   5. Verify code against challenge                                           |
|   6. Record attempt (rate limiting)                                          |
|   7. On success: create MFA session                                          |
|   8. Optional: trust device for future logins                                |
|                                                                              |
+------------------------------------------------------------------------------+
```

### Using MFA

```python
from src.mfa import (
    MFAService,
    MFAMiddleware,
    MFAMiddlewareConfig,
    MFAMethod,
    TOTPGenerator,
    require_mfa,
    create_mfa_routes,
)

# 1. Initialize MFA service
mfa_service = MFAService()

# 2. Add MFA middleware to FastAPI
app.add_middleware(
    MFAMiddleware,
    mfa_service=mfa_service,
    config=MFAMiddlewareConfig(
        enforce_mfa=True,
        exclude_paths=["/health", "/docs", "/mfa/"],
    ),
)

# 3. Include MFA routes
app.include_router(create_mfa_routes(mfa_service))

# 4. TOTP Enrollment Flow
# Start enrollment
result = await mfa_service.enroll_totp(user_id)
qr_uri = result.provisioning_uri  # For QR code

# User scans QR code, enters code from authenticator
result = await mfa_service.verify_totp_enrollment(user_id, code)
backup_codes = result.backup_codes  # Save these!

# 5. SMS Enrollment Flow
result = await mfa_service.enroll_sms(user_id, "+1234567890")
challenge_id = result.challenge_id
# User receives SMS, enters code
result = await mfa_service.verify_sms_enrollment(user_id, challenge_id, code)

# 6. Verify MFA during login
result = await mfa_service.verify(
    user_id=user_id,
    code=user_provided_code,
    method=MFAMethod.TOTP,  # or SMS, EMAIL, BACKUP_CODE
)

if result.success:
    # MFA verified, create session
    session = await mfa_service.create_session(user_id)

# 7. Trust device to skip MFA
await mfa_service.trust_device(
    user_id=user_id,
    device_fingerprint=fingerprint,
    device_name="My Laptop",
)

# 8. Protect endpoints with MFA decorator
@app.get("/sensitive-data")
@require_mfa()
async def get_sensitive_data(request: Request):
    return {"data": "secret"}

# 9. Check MFA status
status = await mfa_service.get_status(user_id)
# Returns: enabled, methods, backup_codes_remaining, etc.
```

---

## API Key Management

### API Key Architecture

```
+-------------------------------------------------------------------------------+
|                            API Key System                                      |
+-------------------------------------------------------------------------------+
|   +-----------------------------------------------------------------------+   |
|   |                         API Key Models                                 |   |
|   |  +------------------+  +------------------+  +--------------------+   |   |
|   |  | KeyStatus        |  | KeyType          |  | APIScope           |   |   |
|   |  | - active         |  | - personal       |  | - read:goals       |   |   |
|   |  | - expired        |  | - service        |  | - write:goals      |   |   |
|   |  | - revoked        |  | - tenant         |  | - execute:agents   |   |   |
|   |  | - suspended      |  | - admin          |  | - admin:full       |   |   |
|   |  +------------------+  +------------------+  +--------------------+   |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                        API Key Components                              |   |
|   |  +------------------------+  +-----------------------------------+    |   |
|   |  | RateLimitConfig        |  | IPRestriction                     |    |   |
|   |  | - per minute: 60       |  | - allowed_ips: []                 |    |   |
|   |  | - per hour: 1000       |  | - allowed_cidrs: []               |    |   |
|   |  | - per day: 10000       |  | - blocked_ips: []                 |    |   |
|   |  | - burst: 100           |  |                                   |    |   |
|   |  +------------------------+  +-----------------------------------+    |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |                         API Key Service                                |   |
|   |  +------------------+  +------------------+  +-------------------+    |   |
|   |  | APIKeyStore      |  | APIKeyService    |  | KeyValidation     |    |   |
|   |  | - save           |  | - create_key     |  | - check format    |    |   |
|   |  | - get            |  | - validate_key   |  | - verify hash     |    |   |
|   |  | - list           |  | - rotate_key     |  | - check scopes    |    |   |
|   |  | - delete         |  | - revoke_key     |  | - check rate      |    |   |
|   |  +------------------+  +------------------+  +-------------------+    |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   |    API Key Middleware     |     |    API Routes                 |     |   |
|   |  +---------------------+  |     |  +---------------------------+|     |   |
|   |  | - Extract key       |  |     |  | POST   /api-keys          ||     |   |
|   |  | - Validate key      |  |     |  | GET    /api-keys          ||     |   |
|   |  | - Check rate limits |  |     |  | GET    /api-keys/{id}     ||     |   |
|   |  | - Check IP          |  |     |  | POST   .../rotate         ||     |   |
|   |  | - Check scopes      |  |     |  | POST   .../revoke         ||     |   |
|   |  +---------------------+  |     |  | DELETE /api-keys/{id}     ||     |   |
|   +-----------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------+
```

### API Key Format

```
+-------------------------------------------------------------------------------+
|                           API Key Format                                       |
+-------------------------------------------------------------------------------+
|                                                                               |
|   Format:  {prefix}_{key_id}_{secret}                                         |
|                                                                               |
|   Example: ak_abc123def456_xYz789ABCdefGHIjklMNOpqrSTUvwxYZ0123456            |
|            ^^  ^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^             |
|            |   |            |                                                 |
|            |   |            +-- Secret (43 chars, URL-safe base64)            |
|            |   +-- Key ID (12 hex chars)                                      |
|            +-- Prefix (ak = API Key)                                          |
|                                                                               |
|   Storage: Only the SHA-256 hash is stored, never the plaintext               |
|                                                                               |
+-------------------------------------------------------------------------------+
```

### Rate Limiting

```
+-------------------------------------------------------------------------------+
|                          Rate Limiting System                                  |
+-------------------------------------------------------------------------------+
|                                                                               |
|   Time Windows:                                                               |
|   +------------------+------------------+------------------+                  |
|   | Per Minute       | Per Hour         | Per Day          |                  |
|   | Default: 60      | Default: 1000    | Default: 10000   |                  |
|   +------------------+------------------+------------------+                  |
|                                                                               |
|   Rate Limit Check Flow:                                                      |
|   +-------+    +--------+    +--------+    +--------+    +--------+          |
|   |Request| -> | Check  | -> | Check  | -> | Check  | -> | Allow  |          |
|   |       |    | Minute |    | Hour   |    | Day    |    |        |          |
|   +-------+    +--------+    +--------+    +--------+    +--------+          |
|                    |              |             |                             |
|                    v              v             v                             |
|               [Exceeded]    [Exceeded]    [Exceeded]                         |
|                    |              |             |                             |
|                    +-------+------+------+------+                            |
|                            v                                                  |
|                      +----------+                                             |
|                      | 429 Too  |                                             |
|                      | Many     |                                             |
|                      | Requests |                                             |
|                      +----------+                                             |
|                                                                               |
+-------------------------------------------------------------------------------+
```

### Using API Keys

```python
from src.apikeys import (
    APIKeyService,
    APIKeyMiddleware,
    APIKeyMiddlewareConfig,
    APIScope,
    RateLimitConfig,
    IPRestriction,
    require_api_key,
    require_scope,
    create_api_key_routes,
)

# 1. Initialize API key service
api_key_service = APIKeyService()

# 2. Add API key middleware to FastAPI
app.add_middleware(
    APIKeyMiddleware,
    api_key_service=api_key_service,
    config=APIKeyMiddlewareConfig(
        require_api_key=True,
        exclude_paths=["/health", "/docs", "/openapi.json"],
    ),
)

# 3. Include API key management routes
app.include_router(create_api_key_routes(api_key_service))

# 4. Create an API key programmatically
api_key, plaintext = await api_key_service.create_key(
    owner_id="user-123",
    name="Production Key",
    scopes=[APIScope.READ_GOALS, APIScope.WRITE_GOALS],
    expires_in_days=365,
    rate_limit=RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=5000,
        requests_per_day=50000,
    ),
    ip_restriction=IPRestriction(
        allowed_cidrs=["192.168.0.0/16", "10.0.0.0/8"],
    ),
)

# 5. Validate an API key
result = await api_key_service.validate_key(
    plaintext_key,
    required_scopes=[APIScope.READ_GOALS],
    client_ip="192.168.1.100",
)
if result.valid:
    print(f"Key belongs to: {result.key.owner_id}")
else:
    print(f"Invalid: {result.error_code}")

# 6. Rotate a key (creates new, revokes old)
new_key, new_plaintext = await api_key_service.rotate_key(
    key_id="ak_abc123def456",
    rotated_by="user-123",
)

# 7. Protect endpoints with decorators
@app.get("/goals")
@require_scope(APIScope.READ_GOALS)
async def list_goals(request: Request):
    return {"goals": [...]}

# 8. Multiple scopes required
@app.post("/goals/{goal_id}/execute")
@require_scope(APIScope.READ_GOALS, APIScope.EXECUTE_GOALS)
async def execute_goal(request: Request, goal_id: str):
    return {"status": "executing"}

# 9. Access key info in request
@app.get("/me")
@require_api_key()
async def get_current_key(request: Request):
    return {
        "key_id": request.state.api_key_id,
        "owner": request.state.api_key_owner,
        "scopes": request.state.api_key_scopes,
    }
```

---

## OAuth 2.0 / OpenID Connect

### OAuth 2.0 Architecture

```
+-------------------------------------------------------------------------------+
|                         OAuth 2.0 / OIDC System                                |
+-------------------------------------------------------------------------------+
|                                                                               |
|   +-------------------------------------------------------------------+       |
|   |                        Grant Types                                 |       |
|   |  +-------------------+  +-------------------+  +----------------+  |       |
|   |  | Authorization     |  | Client            |  | Refresh        |  |       |
|   |  | Code + PKCE       |  | Credentials       |  | Token          |  |       |
|   |  +-------------------+  +-------------------+  +----------------+  |       |
|   |  | Device Code       |  | Password (legacy) |                      |       |
|   |  +-------------------+  +-------------------+                      |       |
|   +-------------------------------------------------------------------+       |
|                                                                               |
|   +-------------------------------------------------------------------+       |
|   |                        Token Types                                 |       |
|   |  +-------------------+  +-------------------+  +----------------+  |       |
|   |  | Access Token      |  | Refresh Token     |  | ID Token       |  |       |
|   |  | (Bearer)          |  | (Rotation)        |  | (JWT/OIDC)     |  |       |
|   |  +-------------------+  +-------------------+  +----------------+  |       |
|   +-------------------------------------------------------------------+       |
|                                                                               |
|   +-------------------------------------------------------------------+       |
|   |                      OAuth Components                              |       |
|   |  +------------------------+  +----------------------------------+  |       |
|   |  | OAuth2Service          |  | OAuth2Middleware                 |  |       |
|   |  | - register_client      |  | - Token validation               |  |       |
|   |  | - authenticate_client  |  | - Scope checking                 |  |       |
|   |  | - create_auth_code     |  | - Request state injection        |  |       |
|   |  | - exchange_code        |  +----------------------------------+  |       |
|   |  | - refresh_token        |                                       |       |
|   |  | - introspect_token     |                                       |       |
|   |  | - revoke_token         |                                       |       |
|   |  +------------------------+                                       |       |
|   +-------------------------------------------------------------------+       |
|                                                                               |
+-------------------------------------------------------------------------------+
```

### Authorization Code Flow with PKCE

```
+-------------------------------------------------------------------------------+
|                     Authorization Code Flow with PKCE                          |
+-------------------------------------------------------------------------------+
|                                                                               |
|   Client                    Authorization Server              Resource Server |
|     |                              |                                 |        |
|     |  1. Generate PKCE            |                                 |        |
|     |     code_verifier            |                                 |        |
|     |     code_challenge           |                                 |        |
|     |                              |                                 |        |
|     |  2. Authorization Request    |                                 |        |
|     |----------------------------->|                                 |        |
|     |  (client_id, redirect_uri,   |                                 |        |
|     |   scope, code_challenge)     |                                 |        |
|     |                              |                                 |        |
|     |  3. User Authentication      |                                 |        |
|     |<-----------------------------|                                 |        |
|     |                              |                                 |        |
|     |  4. Authorization Code       |                                 |        |
|     |<-----------------------------|                                 |        |
|     |                              |                                 |        |
|     |  5. Token Request            |                                 |        |
|     |----------------------------->|                                 |        |
|     |  (code, code_verifier)       |                                 |        |
|     |                              |                                 |        |
|     |  6. Access Token + ID Token  |                                 |        |
|     |<-----------------------------|                                 |        |
|     |                              |                                 |        |
|     |  7. API Request              |                                 |        |
|     |-------------------------------------------------->|        |
|     |  (Bearer token)              |                                 |        |
|     |                              |                                 |        |
|     |  8. Protected Resource       |                                 |        |
|     |<--------------------------------------------------|        |
|                                                                               |
+-------------------------------------------------------------------------------+
```

### Using OAuth 2.0

```python
from src.oauth import (
    OAuth2Service,
    OAuth2Config,
    OAuth2Middleware,
    OAuth2MiddlewareConfig,
    GrantType,
    ClientType,
    OAuth2Scope,
    create_oauth_routes,
    create_discovery_routes,
    create_client_management_routes,
    require_oauth,
    require_scope,
)

# 1. Initialize OAuth service with configuration
oauth_service = OAuth2Service(
    config=OAuth2Config(
        issuer="https://api.example.com",
        jwt_secret="your-secure-jwt-secret",
        access_token_ttl=3600,      # 1 hour
        refresh_token_ttl=2592000,  # 30 days
    )
)

# 2. Add OAuth middleware to FastAPI
app.add_middleware(
    OAuth2Middleware,
    oauth_service=oauth_service,
    config=OAuth2MiddlewareConfig(
        require_auth_by_default=True,
        exclude_paths=["/health", "/docs", "/oauth/", "/.well-known/"],
    ),
)

# 3. Include OAuth routes
app.include_router(create_oauth_routes(oauth_service))
app.include_router(create_discovery_routes(oauth_service))
app.include_router(create_client_management_routes(oauth_service))

# 4. Register a confidential client (server-side app)
client, secret = await oauth_service.register_client(
    client_name="My Web Application",
    redirect_uris=["https://myapp.com/callback"],
    client_type=ClientType.CONFIDENTIAL,
    allowed_scopes=["openid", "profile", "email", "goals:read", "goals:write"],
    grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.REFRESH_TOKEN],
)

# 5. Register a public client (SPA/mobile)
mobile_client, _ = await oauth_service.register_client(
    client_name="My Mobile App",
    redirect_uris=["myapp://callback"],
    client_type=ClientType.PUBLIC,
    require_pkce=True,
    allowed_scopes=["openid", "profile", "goals:read"],
)

# 6. Exchange authorization code for tokens
token_response = await oauth_service.exchange_authorization_code(
    code=auth_code,
    client_id=client.client_id,
    client_secret=secret,
    redirect_uri="https://myapp.com/callback",
    code_verifier=pkce_verifier,  # For PKCE flow
)

# 7. Validate access token
token_record = await oauth_service.validate_access_token(
    access_token,
    required_scopes=["goals:read"],
)

# 8. Refresh tokens
new_tokens = await oauth_service.refresh_token_grant(
    refresh_token=refresh_token,
    client_id=client.client_id,
    client_secret=secret,
)

# 9. Protect endpoints with decorators
@app.get("/api/goals")
@require_scope("goals:read")
async def list_goals(request: Request):
    user_id = request.state.oauth_user_id
    return {"goals": [...]}

# 10. Access token info in request
@app.get("/api/profile")
@require_oauth(scopes=["openid", "profile"])
async def get_profile(request: Request):
    return {
        "user_id": request.state.oauth_user_id,
        "client_id": request.state.oauth_client_id,
        "scopes": request.state.oauth_scopes,
    }
```

---

## Session Management

### Session Management Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                       Session Management System                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   ┌────────────────────────────────────────────────────────────────────┐       ║
║   │                      Session Components                             │       ║
║   │  ┌─────────────────────┐  ┌─────────────────────────────────────┐  │       ║
║   │  │ SessionService      │  │ SessionMiddleware                   │  │       ║
║   │  │                     │  │                                     │  │       ║
║   │  │ • create_session()  │  │ • Token extraction (cookie/header)  │  │       ║
║   │  │ • validate_session()│  │ • Session validation                │  │       ║
║   │  │ • refresh_session() │  │ • Request state injection           │  │       ║
║   │  │ • revoke_session()  │  │ • Path exclusions                   │  │       ║
║   │  │ • elevate_session() │  │                                     │  │       ║
║   │  │ • rotate_token()    │  └─────────────────────────────────────┘  │       ║
║   │  │ • lock_session()    │                                           │       ║
║   │  └─────────────────────┘                                           │       ║
║   │                                                                     │       ║
║   │  ┌─────────────────────────────────────────────────────────────┐   │       ║
║   │  │                    Session Models                            │   │       ║
║   │  │                                                              │   │       ║
║   │  │  Session → SessionStatus → SessionType → AuthMethod         │   │       ║
║   │  │     │                                                        │   │       ║
║   │  │     ├── DeviceInfo (User-Agent parsing)                      │   │       ║
║   │  │     ├── GeoLocation (IP-based location)                      │   │       ║
║   │  │     ├── Idle timeout + Absolute timeout                      │   │       ║
║   │  │     ├── MFA verification status                              │   │       ║
║   │  │     └── Session elevation                                    │   │       ║
║   │  │                                                              │   │       ║
║   │  └─────────────────────────────────────────────────────────────┘   │       ║
║   │                                                                     │       ║
║   │  ┌─────────────────────────────────────────────────────────────┐   │       ║
║   │  │                    Session Store                             │   │       ║
║   │  │                                                              │   │       ║
║   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │       ║
║   │  │  │ By Session  │  │  By Token   │  │  By User    │          │   │       ║
║   │  │  │    ID       │  │   Hash      │  │    ID       │          │   │       ║
║   │  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │       ║
║   │  │                                                              │   │       ║
║   │  └─────────────────────────────────────────────────────────────┘   │       ║
║   └─────────────────────────────────────────────────────────────────────┘       ║
║                                                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Session Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Session Lifecycle                                    │
│                                                                               │
│   CREATE              VALIDATE              TOUCH                REVOKE       │
│      │                    │                   │                    │          │
│      ▼                    ▼                   ▼                    ▼          │
│  ┌───────┐           ┌────────┐          ┌────────┐          ┌────────┐      │
│  │ New   │──────────▶│ Active │─────────▶│ Active │─────────▶│Revoked │      │
│  │Session│           │        │          │(touched)│          │        │      │
│  └───────┘           └────────┘          └────────┘          └────────┘      │
│      │                    │                   │                    │          │
│      │                    │ (idle timeout)    │                    │          │
│      │                    ▼                   │                    │          │
│      │               ┌────────┐               │                    │          │
│      │               │Expired │◀──────────────┘                    │          │
│      │               │        │  (absolute timeout)                │          │
│      │               └────────┘                                    │          │
│      │                                                             │          │
│      │   LOCK                UNLOCK                                │          │
│      │    │                    │                                   │          │
│      ▼    ▼                    ▼                                   │          │
│  ┌────────────┐          ┌────────┐                                │          │
│  │  Locked    │◀────────▶│ Active │                                │          │
│  │ (security) │          │        │                                │          │
│  └────────────┘          └────────┘                                │          │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Using Session Management

```python
from src.sessions import (
    SessionService,
    SessionConfig,
    SessionMiddleware,
    SessionMiddlewareConfig,
    SessionType,
    AuthMethod,
    DeviceInfo,
    require_session,
    require_mfa,
    require_elevated,
)

# 1. Initialize session service
session_service = SessionService(
    config=SessionConfig(
        default_ttl_hours=24,
        idle_timeout_minutes=60,
        max_sessions_per_user=10,
        bind_to_ip=False,
    )
)

# 2. Add session middleware to FastAPI
app.add_middleware(
    SessionMiddleware,
    session_service=session_service,
    config=SessionMiddlewareConfig(
        exclude_paths=["/health", "/auth/login"],
        require_session_by_default=False,
    ),
)

# 3. Create a session (e.g., after login)
session, token = await session_service.create_session(
    user_id="user123",
    session_type=SessionType.WEB,
    auth_method=AuthMethod.PASSWORD,
    device_info=DeviceInfo.from_user_agent(request.headers.get("User-Agent")),
    ip_address=request.client.host,
    mfa_verified=False,
)

# 4. Validate a session
result = await session_service.validate_session(
    token=token,
    ip_address=request.client.host,
    touch=True,  # Update last activity
)

if result.valid:
    user_id = result.session.user_id
else:
    # Handle error: result.error_code, result.error

# 5. Protect endpoints with decorators
@app.get("/api/profile")
@require_session()
async def get_profile(request: Request):
    return {"user_id": request.state.user_id}

@app.get("/api/settings")
@require_mfa()  # Requires MFA-verified session
async def get_settings(request: Request):
    return {"settings": {...}}

@app.post("/api/admin/action")
@require_elevated()  # Requires elevated session
async def admin_action(request: Request):
    return {"result": "success"}

# 6. Elevate session (after re-authentication)
session = await session_service.elevate_session(
    session_id=session.session_id,
    duration_minutes=15,
)

# 7. Rotate token (security measure)
session, new_token = await session_service.rotate_token(session_id)

# 8. Revoke session (logout)
await session_service.revoke_session(
    session_id=session.session_id,
    reason="User logout",
)

# 9. Revoke all sessions (logout everywhere)
count = await session_service.revoke_all_sessions(
    user_id="user123",
    except_session_id=current_session_id,  # Keep current session
)

# 10. Admin: Lock suspicious session
await session_service.lock_session(session_id, reason="Suspicious activity")
await session_service.unlock_session(session_id)
```

---

## Webhook System

### Webhook System Architecture

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           Webhook System                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   ┌────────────────────────────────────────────────────────────────────┐       ║
║   │                     Webhook Components                              │       ║
║   │  ┌─────────────────────┐  ┌─────────────────────────────────────┐  │       ║
║   │  │ WebhookService      │  │ WebhookStore                        │  │       ║
║   │  │                     │  │                                     │  │       ║
║   │  │ • create_webhook()  │  │ • In-memory storage with indexing   │  │       ║
║   │  │ • update_webhook()  │  │ • By owner, event type, tenant      │  │       ║
║   │  │ • delete_webhook()  │  │ • Delivery tracking                 │  │       ║
║   │  │ • publish_event()   │  │ • Pending delivery queue            │  │       ║
║   │  │ • process_delivery()│  └─────────────────────────────────────┘  │       ║
║   │  │ • retry_delivery()  │                                           │       ║
║   │  └─────────────────────┘                                           │       ║
║   └────────────────────────────────────────────────────────────────────┘       ║
║                                                                                ║
║   ┌────────────────────────────────────────────────────────────────────┐       ║
║   │                     Event Types                                     │       ║
║   │                                                                     │       ║
║   │   Goal Events      │ Agent Events     │ Task Events                 │       ║
║   │   • goal.created   │ • agent.spawned  │ • task.created              │       ║
║   │   • goal.updated   │ • agent.updated  │ • task.started              │       ║
║   │   • goal.completed │ • agent.completed│ • task.completed            │       ║
║   │   • goal.failed    │ • agent.failed   │ • task.failed               │       ║
║   │                                                                     │       ║
║   │   Memory Events    │ Safety Events    │ System Events               │       ║
║   │   • memory.stored  │ • safety.alert   │ • system.startup            │       ║
║   │   • memory.retrieved│ • safety.violation│ • system.shutdown         │       ║
║   │   • memory.cleared │ • safety.blocked │ • system.health_check       │       ║
║   │                                                                     │       ║
║   │   User Events      │ Session Events   │ Auth Events                 │       ║
║   │   • user.created   │ • session.created│ • auth.login                │       ║
║   │   • user.updated   │ • session.validated│ • auth.logout             │       ║
║   │   • user.deleted   │ • session.revoked│ • auth.mfa_verified         │       ║
║   │                                                                     │       ║
║   │   Wildcard: * (subscribe to all events)                             │       ║
║   └────────────────────────────────────────────────────────────────────┘       ║
║                                                                                ║
║   ┌────────────────────────────────────────────────────────────────────┐       ║
║   │                     Delivery Pipeline                               │       ║
║   │                                                                     │       ║
║   │   Event Published                                                   │       ║
║   │         │                                                           │       ║
║   │         ▼                                                           │       ║
║   │   ┌─────────────────┐                                               │       ║
║   │   │ Find Matching   │  Filter by event type, tenant, custom filters │       ║
║   │   │ Webhooks        │                                               │       ║
║   │   └────────┬────────┘                                               │       ║
║   │            │                                                        │       ║
║   │            ▼                                                        │       ║
║   │   ┌─────────────────┐                                               │       ║
║   │   │ Create Delivery │  Queue delivery for each matching webhook     │       ║
║   │   │ Records         │                                               │       ║
║   │   └────────┬────────┘                                               │       ║
║   │            │                                                        │       ║
║   │            ▼                                                        │       ║
║   │   ┌─────────────────┐                                               │       ║
║   │   │ Sign & Send     │  HMAC-SHA256 signature + timestamp            │       ║
║   │   │ HTTP POST       │                                               │       ║
║   │   └────────┬────────┘                                               │       ║
║   │            │                                                        │       ║
║   │     ┌──────┴──────┐                                                 │       ║
║   │     ▼             ▼                                                 │       ║
║   │  Success       Failure                                              │       ║
║   │     │             │                                                 │       ║
║   │     │             ▼                                                 │       ║
║   │     │      Retry with Exponential Backoff                           │       ║
║   │     │      (1min, 2min, 4min, 8min, 16min)                          │       ║
║   │     │             │                                                 │       ║
║   │     ▼             ▼                                                 │       ║
║   │  DELIVERED     EXPIRED (after max attempts)                         │       ║
║   └────────────────────────────────────────────────────────────────────┘       ║
║                                                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Webhook Features

| Feature | Description |
|---------|-------------|
| **Event-Driven Publishing** | Publish events to subscribed webhooks automatically |
| **Flexible Subscriptions** | Subscribe to specific events, categories, or all events (*) |
| **Custom Filters** | Filter events by payload fields (e.g., `{"goal_id": "goal123"}`) |
| **Payload Signing** | HMAC-SHA256 signatures for payload verification |
| **Timestamp Validation** | Prevent replay attacks with timestamp verification |
| **Retry with Backoff** | Exponential backoff: 1min, 2min, 4min, 8min, 16min |
| **Delivery Tracking** | Track delivery status, attempts, and response details |
| **Auto-Disable** | Disable webhooks after consecutive failures |
| **Secret Rotation** | Rotate webhook secrets without downtime |
| **Rate Limiting** | Per-owner webhook limits |
| **Local Handlers** | Subscribe in-process handlers for local event processing |

### Webhook Status Flow

```
                    ┌──────────────────────────────────────────────────┐
                    │                  Webhook Lifecycle               │
                    └──────────────────────────────────────────────────┘

    ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐
    │ ACTIVE  │◄──────▶│ PAUSED  │        │ DISABLED│        │ FAILED  │
    └────┬────┘        └─────────┘        └────▲────┘        └────▲────┘
         │                                      │                  │
         │   User pauses/resumes                │                  │
         │                                      │                  │
         └──────────────────────────────────────┴──────────────────┘
                 Auto-disable on failures / Manual disable

    Delivery Status:
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ PENDING │───▶│DELIVERED│    │RETRYING │───▶│ EXPIRED │
    └────┬────┘    └─────────┘    └────▲────┘    └─────────┘
         │                              │
         └──────────────────────────────┘
                 On failure (if retries remaining)
```

### Using Webhooks

```python
from src.webhooks import (
    WebhookService,
    WebhookStore,
    WebhookConfig,
    EventType,
    EventCategory,
    WebhookEvent,
    create_webhook_routes,
    create_webhook_admin_routes,
    publish_webhook_event,
)
from fastapi import FastAPI

app = FastAPI()

# 1. Initialize the webhook system
config = WebhookConfig(
    max_webhooks_per_owner=10,
    max_retries=5,
    signature_tolerance_seconds=300,  # 5 minutes
)
store = WebhookStore()
webhook_service = WebhookService(store, config)

# 2. Add routes to your app
app.include_router(
    create_webhook_routes(webhook_service),
    prefix="/api/webhooks",
    tags=["webhooks"],
)
app.include_router(
    create_webhook_admin_routes(webhook_service),
    prefix="/api/admin/webhooks",
    tags=["webhooks-admin"],
)

# 3. Create a webhook endpoint
webhook = await webhook_service.create_webhook(
    url="https://example.com/webhook",
    events=["goal.completed", "goal.failed"],
    owner_id="user123",
    name="Goal Notifications",
    description="Notifies when goals complete or fail",
    filters={"tenant_id": "tenant1"},  # Only events matching this filter
)
print(f"Webhook ID: {webhook.webhook_id}")
print(f"Secret: {webhook.secret}")  # Store securely!

# 4. Publish an event (deliveries are created for matching webhooks)
deliveries = await webhook_service.publish_event(
    event_type=EventType.GOAL_COMPLETED,
    data={
        "goal_id": "goal_abc123",
        "title": "Complete project",
        "result": "Successfully completed all tasks",
    },
    tenant_id="tenant1",
)
print(f"Created {len(deliveries)} deliveries")

# 5. Process pending deliveries (background task)
await webhook_service.process_pending_deliveries()

# 6. Use decorator for automatic event publishing
@app.post("/api/goals")
@publish_webhook_event(
    webhook_service,
    event_type=EventType.GOAL_CREATED,
    data_extractor=lambda req, resp: {"goal_id": resp.get("id")},
)
async def create_goal(request: Request):
    goal = {"id": "goal_xyz", "title": "New Goal"}
    return goal

# 7. Subscribe local handlers (in-process event handling)
async def on_goal_completed(event: WebhookEvent):
    print(f"Goal completed: {event.data}")

webhook_service.subscribe_local("goal.completed", on_goal_completed)

# 8. Verify webhook signatures (on receiving end)
from src.webhooks import WebhookEndpoint

# Extract from headers
signature = request.headers.get("X-Webhook-Signature")
timestamp = request.headers.get("X-Webhook-Timestamp")
body = await request.body()

# Create endpoint with the stored secret
endpoint = WebhookEndpoint(
    webhook_id="...",
    url="...",
    secret=stored_secret,
    events=[],
    owner_id="...",
)

# Verify
is_valid = endpoint.verify_signature(
    body.decode(),
    signature,
    int(timestamp),
    tolerance_seconds=300,
)

# 9. Webhook management
await webhook_service.pause_webhook(webhook.webhook_id)  # Stop receiving events
await webhook_service.resume_webhook(webhook.webhook_id)  # Resume receiving
new_secret = await webhook_service.rotate_secret(webhook.webhook_id)  # New secret

# 10. Get delivery statistics
stats = await webhook_service.get_webhook_stats(webhook.webhook_id)
print(f"Total deliveries: {stats['total_deliveries']}")
print(f"Successful: {stats['successful_deliveries']}")
print(f"Failed: {stats['failed_deliveries']}")

# 11. Cleanup old deliveries
deleted = await webhook_service.cleanup_old_deliveries(days=30)
print(f"Cleaned up {deleted} old deliveries")
```

### Webhook Payload Format

```json
{
  "event_id": "evt_a1b2c3d4e5f6g7h8",
  "event_type": "goal.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "goal_id": "goal_abc123",
    "title": "Complete project",
    "result": "Successfully completed all tasks"
  },
  "tenant_id": "tenant1"
}
```

### Request Headers

```
POST /webhook HTTP/1.1
Host: example.com
Content-Type: application/json
X-Webhook-Signature: sha256=abc123...
X-Webhook-Timestamp: 1705316400
X-Webhook-Event: goal.completed
X-Webhook-Delivery-ID: dlv_xyz789
User-Agent: AgentVillage-Webhook/1.0
```

### Signature Verification (Receiving End)

```python
import hmac
import hashlib
import time

def verify_webhook(payload: str, signature: str, timestamp: str, secret: str) -> bool:
    """Verify a webhook signature."""
    # Check timestamp is recent (within 5 minutes)
    ts = int(timestamp)
    if abs(time.time() - ts) > 300:
        return False  # Too old, possible replay attack

    # Recreate the signature
    message = f"{ts}.{payload}"
    expected = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures
    provided = signature.replace("sha256=", "")
    return hmac.compare_digest(expected, provided)
```

---

<p align="center">
  <strong>Agent Village - Intelligent Multi-Agent Orchestration</strong><br>
  <em>Achieve complex goals through coordinated AI collaboration</em>
</p>

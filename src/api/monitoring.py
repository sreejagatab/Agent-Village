"""
Real-time Agent Monitoring Dashboard.

Provides a web-based UI for monitoring agent activity,
logs, memory, and system health in real-time.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/monitor", tags=["monitoring"])


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Village Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0f1419;
            color: #e7e9ea;
            min-height: 100vh;
        }

        .header {
            background: #1a2332;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #2f3b4d;
        }

        .header h1 {
            font-size: 1.5rem;
            color: #4a9eff;
        }

        .header .status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #22c55e;
            animation: pulse 2s infinite;
        }

        .status-dot.disconnected {
            background: #ef4444;
            animation: none;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .container {
            display: grid;
            grid-template-columns: 300px 1fr 350px;
            gap: 1rem;
            padding: 1rem;
            height: calc(100vh - 60px);
        }

        .panel {
            background: #1a2332;
            border-radius: 8px;
            border: 1px solid #2f3b4d;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .panel-header {
            padding: 1rem;
            border-bottom: 1px solid #2f3b4d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-header h2 {
            font-size: 1rem;
            color: #8899a6;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 0.5rem;
        }

        /* Agents Panel */
        .agent-card {
            background: #0f1419;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-left: 3px solid #4a9eff;
        }

        .agent-card.busy {
            border-left-color: #f59e0b;
        }

        .agent-card.error {
            border-left-color: #ef4444;
        }

        .agent-card .name {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .agent-card .type {
            font-size: 0.75rem;
            color: #8899a6;
            margin-bottom: 0.5rem;
        }

        .agent-card .metrics {
            display: flex;
            gap: 1rem;
            font-size: 0.75rem;
        }

        .agent-card .metrics span {
            color: #4a9eff;
        }

        /* Log Panel */
        .log-entry {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.75rem;
            padding: 0.5rem;
            border-bottom: 1px solid #2f3b4d;
            word-break: break-all;
        }

        .log-entry .time {
            color: #8899a6;
            margin-right: 0.5rem;
        }

        .log-entry.debug { color: #8899a6; }
        .log-entry.info { color: #4a9eff; }
        .log-entry.warning { color: #f59e0b; }
        .log-entry.error { color: #ef4444; }
        .log-entry.critical { color: #ff4081; background: #2a1a22; }

        .log-entry .category {
            display: inline-block;
            padding: 0 0.25rem;
            border-radius: 3px;
            font-size: 0.65rem;
            margin-right: 0.5rem;
            background: #2f3b4d;
        }

        /* Goals Panel */
        .goal-card {
            background: #0f1419;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }

        .goal-card .description {
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
            color: #e7e9ea;
        }

        .goal-card .status-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            text-transform: uppercase;
        }

        .status-badge.pending { background: #3b4252; color: #8899a6; }
        .status-badge.in_progress { background: #1e3a5f; color: #4a9eff; }
        .status-badge.completed { background: #1a3a2f; color: #22c55e; }
        .status-badge.failed { background: #3a1a1a; color: #ef4444; }

        .goal-card .progress-bar {
            height: 4px;
            background: #2f3b4d;
            border-radius: 2px;
            margin-top: 0.5rem;
            overflow: hidden;
        }

        .goal-card .progress-fill {
            height: 100%;
            background: #4a9eff;
            transition: width 0.3s ease;
        }

        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            padding: 0.5rem;
        }

        .stat-card {
            background: #0f1419;
            padding: 1rem;
            border-radius: 6px;
            text-align: center;
        }

        .stat-card .value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #4a9eff;
        }

        .stat-card .label {
            font-size: 0.7rem;
            color: #8899a6;
            text-transform: uppercase;
        }

        /* Memory Panel */
        .memory-entry {
            background: #0f1419;
            padding: 0.75rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 0.8rem;
        }

        .memory-entry .type {
            display: inline-block;
            padding: 0.125rem 0.375rem;
            border-radius: 3px;
            font-size: 0.65rem;
            margin-right: 0.5rem;
        }

        .memory-entry .type.episodic { background: #3730a3; color: #a5b4fc; }
        .memory-entry .type.semantic { background: #166534; color: #86efac; }
        .memory-entry .type.strategic { background: #9a3412; color: #fdba74; }
        .memory-entry .type.procedural { background: #831843; color: #f9a8d4; }

        .memory-entry .summary {
            margin-top: 0.5rem;
            color: #8899a6;
        }

        /* Filters */
        .filters {
            display: flex;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: #0f1419;
            border-bottom: 1px solid #2f3b4d;
        }

        .filters select, .filters input {
            background: #1a2332;
            border: 1px solid #2f3b4d;
            color: #e7e9ea;
            padding: 0.375rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
        }

        .filters select:focus, .filters input:focus {
            outline: none;
            border-color: #4a9eff;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #0f1419;
        }

        ::-webkit-scrollbar-thumb {
            background: #2f3b4d;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #3f4b5d;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 2rem;
            color: #8899a6;
        }

        .empty-state svg {
            width: 48px;
            height: 48px;
            margin-bottom: 1rem;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏘️ Agent Village Monitor</h1>
        <div class="status">
            <div class="status-dot" id="connection-status"></div>
            <span id="connection-text">Connecting...</span>
        </div>
    </div>

    <div class="container">
        <!-- Agents Panel -->
        <div class="panel">
            <div class="panel-header">
                <h2>Agents</h2>
                <span id="agent-count">0</span>
            </div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value" id="active-agents">0</div>
                    <div class="label">Active</div>
                </div>
                <div class="stat-card">
                    <div class="value" id="busy-agents">0</div>
                    <div class="label">Busy</div>
                </div>
            </div>
            <div class="panel-content" id="agents-list">
                <div class="empty-state">No agents active</div>
            </div>
        </div>

        <!-- Logs Panel -->
        <div class="panel">
            <div class="panel-header">
                <h2>Live Logs</h2>
                <span id="log-count">0</span>
            </div>
            <div class="filters">
                <select id="log-level-filter">
                    <option value="">All Levels</option>
                    <option value="debug">Debug</option>
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="error">Error</option>
                </select>
                <select id="log-category-filter">
                    <option value="">All Categories</option>
                    <option value="agent">Agent</option>
                    <option value="goal">Goal</option>
                    <option value="task">Task</option>
                    <option value="tool">Tool</option>
                    <option value="memory">Memory</option>
                    <option value="system">System</option>
                </select>
                <input type="text" id="log-search" placeholder="Search logs...">
            </div>
            <div class="panel-content" id="logs-list">
                <div class="empty-state">Waiting for logs...</div>
            </div>
        </div>

        <!-- Goals & Memory Panel -->
        <div class="panel">
            <div class="panel-header">
                <h2>Goals</h2>
                <span id="goal-count">0</span>
            </div>
            <div class="panel-content" id="goals-list" style="max-height: 40%;">
                <div class="empty-state">No active goals</div>
            </div>
            <div class="panel-header">
                <h2>Recent Memory</h2>
            </div>
            <div class="panel-content" id="memory-list">
                <div class="empty-state">No recent memories</div>
            </div>
        </div>
    </div>

    <script>
        // State
        const state = {
            connected: false,
            agents: {},
            goals: {},
            logs: [],
            memory: [],
            ws: null,
            logsWs: null,
        };

        // DOM elements
        const elements = {
            connectionStatus: document.getElementById('connection-status'),
            connectionText: document.getElementById('connection-text'),
            agentCount: document.getElementById('agent-count'),
            activeAgents: document.getElementById('active-agents'),
            busyAgents: document.getElementById('busy-agents'),
            agentsList: document.getElementById('agents-list'),
            logCount: document.getElementById('log-count'),
            logsList: document.getElementById('logs-list'),
            goalCount: document.getElementById('goal-count'),
            goalsList: document.getElementById('goals-list'),
            memoryList: document.getElementById('memory-list'),
            logLevelFilter: document.getElementById('log-level-filter'),
            logCategoryFilter: document.getElementById('log-category-filter'),
            logSearch: document.getElementById('log-search'),
        };

        // WebSocket connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            state.ws = new WebSocket(wsUrl);

            state.ws.onopen = () => {
                state.connected = true;
                updateConnectionStatus();
                console.log('WebSocket connected');
            };

            state.ws.onclose = () => {
                state.connected = false;
                updateConnectionStatus();
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };

            state.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            state.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleEvent(data);
            };
        }

        // Connect to logs WebSocket
        function connectLogsWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/logs/stream`;

            state.logsWs = new WebSocket(wsUrl);

            state.logsWs.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    addLog(data.entry);
                }
            };

            state.logsWs.onclose = () => {
                setTimeout(connectLogsWebSocket, 3000);
            };
        }

        // Handle WebSocket events
        function handleEvent(data) {
            const eventType = data.event;

            if (eventType === 'agent.spawned') {
                state.agents[data.agent_id] = {
                    id: data.agent_id,
                    type: data.data.agent_type,
                    name: data.data.name,
                    state: 'idle',
                    metrics: {}
                };
                renderAgents();
            }
            else if (eventType === 'agent.executing') {
                if (state.agents[data.agent_id]) {
                    state.agents[data.agent_id].state = 'busy';
                    state.agents[data.agent_id].currentTask = data.data.task;
                }
                renderAgents();
            }
            else if (eventType === 'agent.completed' || eventType === 'agent.stopped') {
                if (state.agents[data.agent_id]) {
                    state.agents[data.agent_id].state = 'idle';
                    state.agents[data.agent_id].currentTask = null;
                }
                renderAgents();
            }
            else if (eventType === 'goal.created') {
                state.goals[data.goal_id] = {
                    id: data.goal_id,
                    description: data.data.description,
                    status: 'pending',
                    progress: 0
                };
                renderGoals();
            }
            else if (eventType === 'goal.state_changed') {
                if (state.goals[data.goal_id]) {
                    state.goals[data.goal_id].status = data.data.new_state;
                }
                renderGoals();
            }
            else if (eventType === 'goal.progress') {
                if (state.goals[data.goal_id]) {
                    state.goals[data.goal_id].progress = data.data.progress * 100;
                }
                renderGoals();
            }
            else if (eventType === 'system.info' && data.data.log_entry) {
                addLog(data.data.log_entry);
            }
            else if (eventType === 'memory.stored') {
                addMemory(data.data);
            }
        }

        // Add log entry
        function addLog(entry) {
            state.logs.unshift(entry);
            if (state.logs.length > 500) {
                state.logs.pop();
            }
            renderLogs();
        }

        // Add memory entry
        function addMemory(entry) {
            state.memory.unshift(entry);
            if (state.memory.length > 50) {
                state.memory.pop();
            }
            renderMemory();
        }

        // Update connection status
        function updateConnectionStatus() {
            if (state.connected) {
                elements.connectionStatus.classList.remove('disconnected');
                elements.connectionText.textContent = 'Connected';
            } else {
                elements.connectionStatus.classList.add('disconnected');
                elements.connectionText.textContent = 'Disconnected';
            }
        }

        // Render agents
        function renderAgents() {
            const agents = Object.values(state.agents);
            elements.agentCount.textContent = agents.length;
            elements.activeAgents.textContent = agents.filter(a => a.state !== 'error').length;
            elements.busyAgents.textContent = agents.filter(a => a.state === 'busy').length;

            if (agents.length === 0) {
                elements.agentsList.innerHTML = '<div class="empty-state">No agents active</div>';
                return;
            }

            elements.agentsList.innerHTML = agents.map(agent => `
                <div class="agent-card ${agent.state}">
                    <div class="name">${agent.name}</div>
                    <div class="type">${agent.type} | ${agent.state}</div>
                    ${agent.currentTask ? `<div class="task">${agent.currentTask}</div>` : ''}
                    <div class="metrics">
                        <span>Tasks: ${agent.metrics?.tasks_completed || 0}</span>
                        <span>Tokens: ${agent.metrics?.tokens_used || 0}</span>
                    </div>
                </div>
            `).join('');
        }

        // Render logs
        function renderLogs() {
            const levelFilter = elements.logLevelFilter.value;
            const categoryFilter = elements.logCategoryFilter.value;
            const searchTerm = elements.logSearch.value.toLowerCase();

            let logs = state.logs;

            if (levelFilter) {
                const levels = ['debug', 'info', 'warning', 'error', 'critical'];
                const minIndex = levels.indexOf(levelFilter);
                logs = logs.filter(l => levels.indexOf(l.level) >= minIndex);
            }

            if (categoryFilter) {
                logs = logs.filter(l => l.category === categoryFilter);
            }

            if (searchTerm) {
                logs = logs.filter(l => l.message.toLowerCase().includes(searchTerm));
            }

            elements.logCount.textContent = logs.length;

            if (logs.length === 0) {
                elements.logsList.innerHTML = '<div class="empty-state">No logs matching filters</div>';
                return;
            }

            elements.logsList.innerHTML = logs.slice(0, 200).map(log => {
                const time = new Date(log.timestamp).toLocaleTimeString();
                return `
                    <div class="log-entry ${log.level}">
                        <span class="time">${time}</span>
                        <span class="category">${log.category}</span>
                        ${log.message}
                    </div>
                `;
            }).join('');
        }

        // Render goals
        function renderGoals() {
            const goals = Object.values(state.goals);
            elements.goalCount.textContent = goals.length;

            if (goals.length === 0) {
                elements.goalsList.innerHTML = '<div class="empty-state">No active goals</div>';
                return;
            }

            elements.goalsList.innerHTML = goals.map(goal => `
                <div class="goal-card">
                    <div class="description">${goal.description.substring(0, 100)}${goal.description.length > 100 ? '...' : ''}</div>
                    <span class="status-badge ${goal.status}">${goal.status}</span>
                    ${goal.status === 'in_progress' ? `
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${goal.progress}%"></div>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }

        // Render memory
        function renderMemory() {
            if (state.memory.length === 0) {
                elements.memoryList.innerHTML = '<div class="empty-state">No recent memories</div>';
                return;
            }

            elements.memoryList.innerHTML = state.memory.map(mem => `
                <div class="memory-entry">
                    <span class="type ${mem.memory_type}">${mem.memory_type}</span>
                    <span>${mem.summary || 'No summary'}</span>
                </div>
            `).join('');
        }

        // Fetch initial data
        async function fetchInitialData() {
            try {
                // Fetch agents
                const agentsRes = await fetch('/agents');
                if (agentsRes.ok) {
                    const agents = await agentsRes.json();
                    agents.forEach(agent => {
                        state.agents[agent.id] = agent;
                    });
                    renderAgents();
                }

                // Fetch goals
                const goalsRes = await fetch('/goals?limit=10');
                if (goalsRes.ok) {
                    const data = await goalsRes.json();
                    data.goals.forEach(goal => {
                        state.goals[goal.id] = goal;
                    });
                    renderGoals();
                }

                // Fetch recent logs
                const logsRes = await fetch('/api/logs?limit=100');
                if (logsRes.ok) {
                    const data = await logsRes.json();
                    state.logs = data.logs.reverse();
                    renderLogs();
                }
            } catch (error) {
                console.error('Error fetching initial data:', error);
            }
        }

        // Event listeners for filters
        elements.logLevelFilter.addEventListener('change', renderLogs);
        elements.logCategoryFilter.addEventListener('change', renderLogs);
        elements.logSearch.addEventListener('input', renderLogs);

        // Initialize
        connectWebSocket();
        connectLogsWebSocket();
        fetchInitialData();

        // Refresh agents every 10 seconds
        setInterval(async () => {
            try {
                const res = await fetch('/agents');
                if (res.ok) {
                    const agents = await res.json();
                    state.agents = {};
                    agents.forEach(agent => {
                        state.agents[agent.id] = agent;
                    });
                    renderAgents();
                }
            } catch (e) {
                console.error('Failed to refresh agents:', e);
            }
        }, 10000);
    </script>
</body>
</html>
"""


@router.get("", response_class=HTMLResponse)
async def get_dashboard():
    """
    Serve the real-time monitoring dashboard.

    Access at /monitor to view the live dashboard.
    """
    return HTMLResponse(content=DASHBOARD_HTML)


@router.get("/health")
async def monitor_health():
    """Get monitoring system health status."""
    from src.api.websocket import get_connection_manager
    from src.api.log_streaming import get_log_buffer

    ws_manager = get_connection_manager()
    log_buffer = get_log_buffer()

    return {
        "status": "healthy",
        "websocket": ws_manager.get_stats(),
        "log_buffer": await log_buffer.get_stats(),
    }

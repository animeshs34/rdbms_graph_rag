// RDBMS to Graph RAG - Frontend Application

const API_BASE = 'http://localhost:8000';

// Tab Navigation
function switchTab(tabName, event) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from all nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    if (event && event.target) {
        event.target.classList.add('active');
    }

    // Load data for specific tabs
    if (tabName === 'admin') {
        loadStats();
    } else if (tabName === 'databases') {
        loadDatabases();
    }
}

// Admin Functions
async function migrateDatabase() {
    const dbType = document.getElementById('dbType').value;
    const domainPrefix = document.getElementById('domainPrefix').value;
    const clearTarget = document.getElementById('clearTarget').checked;
    
    const statusDiv = document.getElementById('migrateStatus');
    statusDiv.innerHTML = '<div class="spinner"></div><p>Migrating database...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/migrate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                db_type: dbType,
                clear_target: clearTarget,
                domain_prefix: domainPrefix
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="status-message status-success">
                    ✅ Migration successful! 
                    ${data.nodes_created} nodes and ${data.relationships_created} relationships created.
                </div>
            `;
            loadStats();
        } else {
            statusDiv.innerHTML = `
                <div class="status-message status-error">
                    ❌ Error: ${data.detail || 'Migration failed'}
                </div>
            `;
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="status-message status-error">
                ❌ Error: ${error.message}
            </div>
        `;
    }
}

async function buildEmbeddings() {
    const nodeLabels = document.getElementById('nodeLabels').value
        .split(',')
        .map(s => s.trim())
        .filter(s => s);
    
    const statusDiv = document.getElementById('embeddingStatus');
    statusDiv.innerHTML = '<div class="spinner"></div><p>Building embeddings...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/embeddings/build`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                node_labels: nodeLabels.length > 0 ? nodeLabels : null
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.innerHTML = `
                <div class="status-message status-success">
                    ✅ Embeddings built! ${data.embeddings_created} embeddings created.
                </div>
            `;
            // Refresh vector store status
            checkVectorStoreStatus();
        } else {
            statusDiv.innerHTML = `
                <div class="status-message status-error">
                    ❌ Error: ${data.detail || 'Embedding creation failed'}
                </div>
            `;
        }
    } catch (error) {
        statusDiv.innerHTML = `
            <div class="status-message status-error">
                ❌ Error: ${error.message}
            </div>
        `;
    }
}

async function checkVectorStoreStatus() {
    try {
        const response = await fetch(`${API_BASE}/embeddings/status`);
        const data = await response.json();

        const statusEl = document.getElementById('vsStatus');
        const sizeEl = document.getElementById('vsSize');
        const autoSaveEl = document.getElementById('vsAutoSave');

        if (data.is_loaded) {
            statusEl.innerHTML = '<span style="color: green;">✅ Loaded</span>';
        } else {
            statusEl.innerHTML = '<span style="color: orange;">⚠️ Empty</span>';
        }

        sizeEl.textContent = data.size || 0;
        autoSaveEl.textContent = data.auto_save ? 'Enabled' : 'Disabled';

    } catch (error) {
        console.error('Error checking vector store status:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        // Also load vector store status
        checkVectorStoreStatus();
        
        document.getElementById('statsDisplay').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${data.total_nodes || 0}</div>
                    <div class="stat-label">Total Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.total_relationships || 0}</div>
                    <div class="stat-label">Relationships</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.node_types?.length || 0}</div>
                    <div class="stat-label">Node Types</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.relationship_types?.length || 0}</div>
                    <div class="stat-label">Relationship Types</div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-header">Node Types</div>
                <ul>
                    ${data.node_types?.map(nt => `
                        <li><strong>${nt.label}</strong>: ${nt.count} nodes</li>
                    `).join('') || '<li>No data</li>'}
                </ul>
            </div>
        `;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Query Functions
async function executeQuery() {
    const query = document.getElementById('queryInput').value.trim();
    
    if (!query) {
        alert('Please enter a query');
        return;
    }
    
    const resultsDiv = document.getElementById('queryResults');
    resultsDiv.innerHTML = '<div class="spinner"></div><p>Processing your query...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayQueryResults(data);
        } else {
            resultsDiv.innerHTML = `
                <div class="status-message status-error">
                    ❌ Error: ${data.detail || 'Query failed'}
                </div>
            `;
        }
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="status-message status-error">
                ❌ Error: ${error.message}
            </div>
        `;
    }
}

function displayQueryResults(data) {
    const resultsDiv = document.getElementById('queryResults');
    
    let html = `
        <div class="result-card">
            <div class="result-header">📋 Answer</div>
            <div class="result-content">${data.answer || 'No answer generated'}</div>
        </div>
    `;
    
    if (data.context) {
        html += `
            <div class="result-card">
                <div class="result-header">🔍 Retrieved Context</div>
                <div class="result-content">
                    <pre style="white-space: pre-wrap; font-size: 12px;">${data.context}</pre>
                </div>
            </div>
        `;
    }
    
    if (data.cypher_query) {
        html += `
            <div class="result-card">
                <div class="result-header">💾 Cypher Query</div>
                <div class="result-content">
                    <pre style="background: #f3f4f6; padding: 12px; border-radius: 4px; overflow-x: auto;">${data.cypher_query}</pre>
                </div>
            </div>
        `;
    }
    
    resultsDiv.innerHTML = html;
}

// Sample Queries
function loadSampleQuery(query) {
    document.getElementById('queryInput').value = query;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Load initial stats
    loadStats();
    
    // Add enter key support for query input
    document.getElementById('queryInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            executeQuery();
        }
    });
});


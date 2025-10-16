# Web UI for RDBMS to Graph RAG

A simple, minimal single-page web interface for the RDBMS to Graph RAG system.

## Features

### 📊 Migrate Database
- Migrate relational databases (PostgreSQL, MySQL, SQLite) to Neo4j knowledge graph
- Support for domain prefixes to isolate different databases
- Option to clear existing graph data
- Real-time migration status

### 🔍 Query Graph
- Natural language queries against the knowledge graph
- Intelligent retrieval using RAG (Retrieval-Augmented Generation)
- Display query results with formatted answers

### ⚡ Real-time Sync (CDC)
- Setup Change Data Capture for PostgreSQL
- Real-time synchronization of database changes to graph
- Start/Stop/Restart CDC controls

## Access

Once the API server is running, access the UI at:

```
http://localhost:8000/
```

Or if deployed:
```
https://your-deployment-url.com/
```

## Usage

### 1. Migrate a Database

1. Go to the "Migrate Database" tab
2. Select your database type (PostgreSQL, MySQL, or SQLite)
3. Enter connection string (or leave empty to use default)
4. Optionally add a domain prefix (e.g., "Ecommerce", "Healthcare")
5. Check "Clear existing graph data" if you want to start fresh
6. Click "Start Migration"

Example connection strings:
- PostgreSQL: `postgresql://user:password@localhost:5432/dbname`
- MySQL: `mysql://user:password@localhost:3306/dbname`
- SQLite: `sqlite:///path/to/database.db`

### 2. Query the Graph

1. Go to the "Query Graph" tab
2. Enter your natural language query
3. Click "Execute Query"
4. View the AI-generated answer and full results

Example queries:
- "Show me all customers who made purchases in the last month"
- "What are the most popular products?"
- "Find all orders with a total amount greater than $1000"

### 3. Setup Real-time Sync

1. Go to the "Real-time Sync" tab
2. Select database type (currently PostgreSQL only)
3. Enter connection string
4. Add domain prefix
5. Click "Setup CDC"
6. Use Start/Stop/Restart buttons to control synchronization

## Design

The UI is designed to be:
- **Minimal**: Single HTML file with embedded CSS and JavaScript
- **Responsive**: Works on desktop and mobile devices
- **Modern**: Clean gradient design with smooth animations
- **User-friendly**: Clear labels, helpful tooltips, and error messages

## Technical Details

- Pure HTML/CSS/JavaScript (no frameworks)
- Uses Fetch API for backend communication
- Responsive design with flexbox
- Gradient purple theme
- Loading spinners for async operations
- Success/error message displays

## File Structure

```
src/web/
├── templates/
│   └── index.html    # Single-page UI
├── static/           # (Reserved for future assets)
└── README.md         # This file
```

## API Endpoints Used

- `POST /migrate` - Migrate database to graph
- `POST /query` - Execute natural language query
- `POST /cdc/setup` - Setup Change Data Capture
- `POST /cdc/control` - Control CDC (start/stop/restart)

## Future Enhancements

Potential improvements:
- [ ] Add schema visualization
- [ ] Show migration progress bar
- [ ] Display graph statistics
- [ ] Add query history
- [ ] Export query results
- [ ] Dark mode toggle
- [ ] Multi-language support


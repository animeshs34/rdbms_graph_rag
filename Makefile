.PHONY: help install setup build up down start stop restart logs clean clean-all test test-all api migrate embeddings query cdc-setup cdc-start cdc-stop cdc-status health fresh-build fresh-start docker-clean docker-prune

include .env
export

help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         RDBMS to Graph RAG - Makefile Commands                 ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 Setup & Installation:"
	@echo "  make install        Install Python dependencies"
	@echo "  make setup          Complete setup (env + Docker + build)"
	@echo "  make build          Build Docker images"
	@echo ""
	@echo "🐳 Docker Management:"
	@echo "  make up             Start all Docker services"
	@echo "  make down           Stop and remove containers"
	@echo "  make start          Start stopped containers"
	@echo "  make stop           Stop running containers"
	@echo "  make restart        Restart all services"
	@echo "  make logs           View Docker logs (all services)"
	@echo "  make logs-postgres  View PostgreSQL logs"
	@echo "  make logs-mysql     View MySQL logs"
	@echo "  make logs-neo4j     View Neo4j logs"
	@echo "  make logs-redis     View Redis logs"
	@echo ""
	@echo "🔧 Application:"
	@echo "  make api            Start API server (local)"
	@echo "  make migrate        Run database migration"
	@echo "  make embeddings     Build embeddings for graph data"
	@echo "  make query          Run a test query"
	@echo "  make health         Check service health"
	@echo ""
	@echo "📊 CDC (Change Data Capture):"
	@echo "  make cdc-setup      Setup CDC for PostgreSQL"
	@echo "  make cdc-start      Start CDC streaming"
	@echo "  make cdc-stop       Stop CDC streaming"
	@echo "  make cdc-status     Check CDC status"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean          Clean temporary files"
	@echo "  make clean-all      Clean everything (Docker + files + data)"
	@echo "  make clean-data     Clean vector store data"
	@echo "  make clean-neo4j    Clear all Neo4j data"
	@echo "  make docker-clean   Remove all containers and images"
	@echo "  make docker-prune   Deep clean Docker (removes volumes too)"
	@echo ""
	@echo "🔄 Fresh Build:"
	@echo "  make fresh-build    Clean everything and rebuild from scratch"
	@echo "  make fresh-start    Fresh build + start all services"
	@echo ""
	@echo "🧪 Testing & Development:"
	@echo "  make test           Run unit tests"
	@echo "  make test-all       Run comprehensive integration tests"
	@echo "  make format         Format code with black"
	@echo "  make lint           Run linters"
	@echo ""

install:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

setup:
	@echo "🚀 Setting up RDBMS to Graph RAG..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "⚠️  Created .env file - Please configure your API keys!"; \
		echo "   Edit .env and add:"; \
		echo "   - GEMINI_API_KEY or OPENAI_API_KEY"; \
		exit 1; \
	fi
	@echo "🐳 Building Docker images..."
	@$(MAKE) build
	@echo "🐳 Starting Docker services..."
	@$(MAKE) up
	@echo "⏳ Waiting for services to be ready..."
	@sleep 15
	@$(MAKE) health
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "📝 Next steps:"
	@echo "  1. make api          # Start API server"
	@echo "  2. make migrate      # Migrate database to graph"
	@echo "  3. make embeddings   # Build embeddings"
	@echo "  4. make query        # Test a query"
	@echo ""
	@echo "🌐 Access Points:"
	@echo "  Web UI:   http://localhost:8000/"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Neo4j:    http://localhost:7474 (neo4j/neo4jpassword)"
	@echo ""

build:
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Docker images built"

up:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d
	@echo "✅ Services started"

down:
	@echo "🛑 Stopping Docker services..."
	docker-compose down
	@echo "✅ Services stopped"

start:
	@echo "▶️  Starting containers..."
	docker-compose start
	@echo "✅ Containers started"

stop:
	@echo "⏸️  Stopping containers..."
	docker-compose stop
	@echo "✅ Containers stopped"

restart:
	@echo "🔄 Restarting services..."
	@$(MAKE) stop
	@$(MAKE) start
	@echo "✅ Services restarted"

logs:
	docker-compose logs -f

logs-postgres:
	@echo "📋 Viewing PostgreSQL logs..."
	docker-compose logs -f postgres

logs-mysql:
	@echo "📋 Viewing MySQL logs..."
	docker-compose logs -f mysql

logs-neo4j:
	@echo "📋 Viewing Neo4j logs..."
	docker-compose logs -f neo4j

logs-redis:
	@echo "📋 Viewing Redis logs..."
	docker-compose logs -f redis

api:
	@echo "🚀 Starting API server (local)..."
	@echo "📖 API docs: http://localhost:8000/docs"
	@echo "🌐 Web UI: http://localhost:8000/"
	@echo "🏥 Health: http://localhost:8000/health"
	@echo ""
	python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	@echo "🔄 Running database migration..."
	@echo "Source: PostgreSQL (localhost:5432/sample_db)"
	@echo "Target: Neo4j (localhost:7687)"
	@echo "Domain: Healthcare"
	@echo ""
	@curl -s -X POST http://localhost:8000/migrate \
		-H "Content-Type: application/json" \
		-d '{"db_type": "postgres", "connection_string": "postgresql://postgres:postgres@localhost:5432/sample_db", "domain_prefix": "Healthcare", "batch_size": 1000}' \
		| python3 -m json.tool || echo "❌ Migration failed. Is API running? (make api)"
	@echo ""
	@echo "✅ Migration complete. Check Neo4j at http://localhost:7474"

embeddings:
	@echo "🔮 Building embeddings for graph data..."
	@echo "Domain: Healthcare"
	@echo ""
	@curl -s -X POST http://localhost:8000/embeddings/build \
		-H "Content-Type: application/json" \
		-d '{"domain_prefix": "Healthcare"}' \
		| python3 -m json.tool || echo "❌ Embeddings build failed. Is API running?"
	@echo ""
	@echo "⏳ Waiting for embeddings to build (this may take a minute)..."
	@sleep 15
	@echo "✅ Checking embeddings status..."
	@curl -s http://localhost:8000/embeddings/status | python3 -m json.tool

query:
	@echo "💬 Running test query..."
	@echo "Query: How many patients are in the database?"
	@echo ""
	@curl -s -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"query": "How many patients are in the database?"}' \
		| python3 -m json.tool || echo "❌ Query failed. Is API running?"

health:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo -n "PostgreSQL: "
	@docker exec rdbms_postgres pg_isready -U postgres > /dev/null 2>&1 && echo "✅ Connected" || echo "❌ Not running"
	@echo -n "MySQL:      "
	@docker exec rdbms_mysql mysql -u root -pmysql -e "SELECT 1;" > /dev/null 2>&1 && echo "✅ Connected" || echo "❌ Not running"
	@echo -n "Neo4j:      "
	@docker exec rdbms_neo4j cypher-shell -u neo4j -p neo4jpassword "RETURN 1;" > /dev/null 2>&1 && echo "✅ Connected" || echo "❌ Not running"
	@echo -n "Redis:      "
	@docker exec rdbms_redis redis-cli PING > /dev/null 2>&1 && echo "✅ Connected" || echo "❌ Not running"
	@echo -n "API:        "
	@curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✅ Running at http://localhost:8000" || echo "❌ Not running (start with: make api)"
	@echo ""

cdc-setup:
	@echo "📡 Setting up CDC for PostgreSQL..."
	@curl -X POST http://localhost:8000/cdc/setup \
		-H "Content-Type: application/json" \
		-d '{"db_type": "postgres", "domain_prefix": "Healthcare"}' \
		2>/dev/null | python3 -m json.tool || echo "❌ CDC setup failed"

cdc-start:
	@echo "▶️  Starting CDC streaming..."
	@curl -X POST http://localhost:8000/cdc/control \
		-H "Content-Type: application/json" \
		-d '{"action": "start"}' \
		2>/dev/null | python3 -m json.tool || echo "❌ CDC start failed"

cdc-stop:
	@echo "⏸️  Stopping CDC streaming..."
	@curl -X POST http://localhost:8000/cdc/control \
		-H "Content-Type: application/json" \
		-d '{"action": "stop"}' \
		2>/dev/null | python3 -m json.tool || echo "❌ CDC stop failed"

cdc-status:
	@echo "📊 CDC Status:"
	@curl -s http://localhost:8000/cdc/status 2>/dev/null | python3 -m json.tool || echo "❌ Failed to get CDC status"

clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✅ Temporary files cleaned"

clean-data:
	@echo "🗑️  Cleaning vector store data..."
	@rm -rf data/vector_store/*
	@echo "✅ Vector store data cleaned"

clean-neo4j:
	@echo "🗑️  Clearing all Neo4j data..."
	@docker exec rdbms_neo4j cypher-shell -u neo4j -p neo4jpassword "MATCH (n) DETACH DELETE n;" 2>/dev/null || echo "❌ Neo4j not running"
	@echo "✅ Neo4j data cleared"

clean-all: clean
	@echo "🗑️  Removing all Docker resources..."
	docker-compose down -v --remove-orphans
	@$(MAKE) clean-data
	@echo "✅ Everything cleaned"

test:
	@echo "🧪 Running unit tests..."
	pytest tests/ -v

test-all:
	@echo "🧪 Running comprehensive integration tests..."
	@echo "⚠️  Make sure API is running (make api) and Docker services are up (make up)"
	@echo ""
	@chmod +x test_system.sh
	@./test_system.sh

format:
	@echo "🎨 Formatting code..."
	black src/ tests/

lint:
	@echo "🔍 Running linters..."
	flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503

docker-clean:
	@echo "🧹 Cleaning Docker containers and images..."
	@echo "Stopping all containers..."
	@docker-compose down 2>/dev/null || true
	@echo "Removing project containers..."
	@docker ps -a | grep rdbms_ | awk '{print $$1}' | xargs docker rm -f 2>/dev/null || true
	@echo "Removing project images..."
	@docker images | grep rdbms | awk '{print $$3}' | xargs docker rmi -f 2>/dev/null || true
	@echo "✅ Docker containers and images cleaned"

docker-prune:
	@echo "🧹 Deep cleaning Docker (including volumes)..."
	@docker-compose down -v --remove-orphans 2>/dev/null || true
	@docker ps -a | grep rdbms_ | awk '{print $$1}' | xargs docker rm -f 2>/dev/null || true
	@docker images | grep rdbms | awk '{print $$3}' | xargs docker rmi -f 2>/dev/null || true
	@docker volume ls | grep rdbms | awk '{print $$2}' | xargs docker volume rm 2>/dev/null || true
	@echo "✅ Docker deep clean complete"

fresh-build: docker-prune clean
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║              🔄 FRESH BUILD FROM SCRATCH                       ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Step 1/3: Building Docker images..."
	@docker-compose build --no-cache --progress=plain
	@echo ""
	@echo "✅ Fresh build complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. make up              # Start all services"
	@echo "  2. make api-docker      # Start API in Docker"
	@echo "  3. make migrate-docker  # Run migration"
	@echo ""
	@echo "Or use: make fresh-start (does all of the above)"

fresh-start: fresh-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║              🚀 STARTING ALL SERVICES                          ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Step 2/3: Starting all services..."
	@docker-compose up -d
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo ""
	@echo "📊 Step 3/3: Service Status:"
	@docker-compose ps
	@echo ""
	@$(MAKE) health
	@echo ""
	@echo "✅ All services started!"
	@echo ""
	@echo "🌐 Access Points:"
	@echo "  Web UI:   http://localhost:8000/"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Neo4j:    http://localhost:7474 (neo4j/neo4jpassword)"
	@echo ""
	@echo "📝 Next steps:"
	@echo "  make api        # Start API server"
	@echo "  make migrate    # Migrate database to graph"
	@echo "  make embeddings # Build embeddings"
	@echo "  make query      # Test a query"
	@echo "  make test-all   # Run all integration tests"

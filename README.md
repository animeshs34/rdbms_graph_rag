# 🔄 RDBMS to Graph RAG

> **Transform relational databases into intelligent knowledge graphs with natural language querying**


[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![Status: Prototype](https://img.shields.io/badge/status-prototype-orange.svg)](https://github.com)

**PROTOTYPE STATUS**: This is a research prototype and proof-of-concept. Not recommended for production use without significant hardening and testing.

---

## Architecture Overview

<div align="center">
  <img src="docs/images/architecture_daig.png" alt="RelationalDB to GraphRAG Production Architecture" width="100%">
  <p><em>Scalable, Observable, and Explainable architecture for transforming relational databases into intelligent knowledge graphs</em></p>
</div>

## Demo Screen
<div align="center">
 <img src="https://drive.google.com/uc?export=view&id=1_qFC9_YGk0zjTeXol519eWbTuWJnOWLG" alt="Working Demo" width="100%">
</div>
---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [API Documentation](#-api-documentation)
- [Configuration](#-configuration)
- [Development](#-development)
- [Roadmap](#-roadmap)

---

## Overview

RDBMS to Graph RAG is an experimental system that automatically converts relational databases (PostgreSQL, MySQL, SQLite) into Neo4j knowledge graphs and enables natural language querying using Retrieval-Augmented Generation (RAG).

### What Makes This Unique?

- ** AI-Powered Schema Mapping**: Uses LLMs (OpenAI/Gemini) to intelligently infer relationships beyond foreign keys
- ** Multi-Database Support**: Works with PostgreSQL, MySQL, and SQLite
- ** Domain Isolation**: Migrate multiple databases into a single Neo4j instance with namespace prefixing
- ** Natural Language Queries**: Ask questions in plain English, get structured answers from your graph
- ** Real-time Sync (Experimental)**: CDC support for keeping graph database synchronized with source
- ** Vector Embeddings**: Semantic search capabilities using OpenAI or Gemini embeddings

### Use Cases

-  **Research**: Exploring graph-based representations of relational data
-  **Data Analysis**: Understanding complex relationships in legacy databases
-  **Prototyping**: Building proof-of-concepts for graph-based applications
-  **Learning**: Understanding RAG, knowledge graphs, and LLM integration

---

##  Key Features

### Core Capabilities

| Feature | Description | Status |
|---------|-------------|--------|
| **Schema Mapping** | Automatic conversion of relational schemas to graph schemas |  Stable |
| **LLM Enhancement** | AI-powered relationship inference from metadata |  Stable |
| **Data Migration** | Batch migration of data from RDBMS to Neo4j |  Stable |
| **Vector Embeddings** | Generate embeddings for semantic search |  Stable |
| **Natural Language Query** | RAG-powered query interface |  Experimental |
| **Change Data Capture** | Real-time sync from PostgreSQL ([Setup Guide](CDC_SETUP.md)) |  Experimental |
| **Multi-tenancy** | Domain prefixing for database isolation |  Stable |

### Supported Technologies

**Source Databases:**
- PostgreSQL 12+
- MySQL 8.0+
- SQLite 3+

**Target Graph Database:**
- Neo4j 5.x (Community/Enterprise)

**LLM Providers:**
- OpenAI (GPT-4, GPT-3.5)
- Google Gemini (gemini-2.5-flash, gemini-1.5-pro)

**Embedding Providers:**
- OpenAI (text-embedding-3-small/large)
- Google Gemini (text-embedding-004)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Client Applications                          │
│              (Web UI, API Clients, Dashboards)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI REST API                              │
│         (Schema Mapping, Migration, Query, Embeddings)           │
└─────┬──────────┬──────────┬──────────┬─────────────────────────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
┌──────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│ RDBMS    │ │ Neo4j│ │ Vector  │ │   LLM    │
│Connectors│ │ Graph│ │  Store  │ │ Provider │
└──────────┘ └──────┘ └─────────┘ └──────────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
┌──────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│PostgreSQL│ │ Neo4j│ │ Chroma/ │ │ OpenAI/  │
│  MySQL   │ │  DB  │ │ FAISS   │ │ Gemini   │
│  SQLite  │ │      │ │         │ │          │
└──────────┘ └──────┘ └─────────┘ └──────────┘
```

### Data Flow

1. **Schema Discovery**: Connect to source RDBMS and extract schema metadata
2. **LLM Enhancement**: Send metadata to LLM to infer additional relationships
3. **Graph Schema Generation**: Create Neo4j node and relationship types
4. **Data Migration**: Batch transfer data from RDBMS to Neo4j
5. **Embedding Generation**: Create vector embeddings for graph nodes
6. **Query Processing**: Use RAG to answer natural language questions

---

### 💻 Local Installation

#### Prerequisites

- **Docker & Docker Compose** (required)
- **Python 3.11+** (for local development)
- **API Key**: OpenAI or Google Gemini

#### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rdbms_graph_rag.git
cd rdbms_graph_rag

# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# For Gemini (recommended - has free tier):
#   GEMINI_API_KEY=your_key_here
# For OpenAI:
#   OPENAI_API_KEY=your_key_here

# Start all services
make setup
```

This will:
- Build Docker images
- Start PostgreSQL, MySQL, Neo4j, Redis
- Load sample healthcare database
- Initialize the API server

### Verify Installation

```bash
# Check service health
make health

# Run comprehensive tests
./test_system.sh
```

### Access Points

- **Web UI**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474 (neo4j/neo4jpassword)

---

##  Usage Examples

### 1. Migrate a Database

```bash
# Using Makefile
make migrate CONNECTION_STRING="postgresql://user:pass@host:5432/mydb" DOMAIN="MyApp"

# Using API
curl -X POST http://localhost:8000/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "db_type": "postgres",
    "connection_string": "postgresql://user:pass@host:5432/mydb",
    "domain_prefix": "MyApp",
    "use_llm": true,
    "batch_size": 1000
  }'
```

### 2. Build Vector Embeddings

```bash
# Using Makefile
make embeddings DOMAIN="MyApp"

# Using API
curl -X POST http://localhost:8000/embeddings/build \
  -H "Content-Type: application/json" \
  -d '{
    "domain_prefix": "MyApp",
    "batch_size": 100
  }'
```

### 3. Query with Natural Language

```bash
# Using Makefile
make query QUESTION="Show me all customers who placed orders in the last month"

# Using API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all customers who placed orders in the last month",
    "domain_prefix": "MyApp"
  }'
```

### 4. Python SDK Example

```python
import requests

API_URL = "http://localhost:8000"

# Migrate database
response = requests.post(f"{API_URL}/migrate", json={
    "db_type": "postgres",
    "connection_string": "postgresql://localhost:5432/mydb",
    "domain_prefix": "MyApp",
    "use_llm": True
})
print(f"Migrated: {response.json()['nodes_created']} nodes")

# Query
response = requests.post(f"{API_URL}/query", json={
    "query": "How many users are active?",
    "domain_prefix": "MyApp"
})
print(response.json()["answer"])
```

---

##  API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/schema/map` | POST | Map RDBMS schema to graph schema |
| `/migrate` | POST | Migrate data to Neo4j |
| `/embeddings/build` | POST | Generate vector embeddings |
| `/query` | POST | Natural language query |
| `/stats` | GET | Graph statistics |

### Interactive API Docs

Visit http://localhost:8000/docs for full Swagger/OpenAPI documentation with interactive testing.

---

##  Configuration

### Environment Variables

```bash
# LLM Provider (openai or gemini)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash

# Embedding Provider
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Database Connections
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword

# API Configuration
API_PORT=8000
LOG_LEVEL=INFO
```

See `.env.example` for complete configuration options.

---

##  Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start services
make up

# Run API locally
make api
```

### Running Tests

```bash
# All tests
./test_system.sh

# Individual tests
./test_system.sh health
./test_system.sh schema
./test_system.sh migrate
./test_system.sh query
```

### Project Structure

```
rdbms_graph_rag/
├── src/
│   ├── api/              # FastAPI application
│   ├── connectors/       # Database connectors
│   ├── schema_mapper/    # Schema mapping logic
│   ├── migration/        # Data migration
│   ├── embeddings/       # Vector embeddings
│   ├── retrieval/        # RAG query engine
│   ├── llm/              # LLM provider abstraction
│   └── cdc/              # Change Data Capture
├── docker/               # Docker configurations
├── sample_data/          # Sample databases
├── tests/                # Unit tests
├── test_system.sh        # Integration tests
└── Makefile              # Common commands
```

---

##  Roadmap

### Current Status (v0.1.0 - Prototype)

- ✅ Basic schema mapping
- ✅ LLM-enhanced relationship inference
- ✅ Data migration for PostgreSQL, MySQL, SQLite
- ✅ Vector embeddings with OpenAI/Gemini
- ✅ Basic RAG query interface
- ✅ Web UI prototype

### Features Planned for Future Releases

- [ ] **v0.2.0**: Production-ready CDC for PostgreSQL
- [ ] **v0.3.0**: Advanced query optimization
- [ ] **v0.4.0**: Multi-hop reasoning in RAG
- [ ] **v0.5.0**: Incremental schema updates
- [ ] **v1.0.0**: Production hardening, security audit

### Research and Exploration Areas

-  Graph neural networks for better embeddings
-  Automated schema evolution detection
-  Cross-database query federation
-  Explainable AI for query results

---


##  Disclaimer

This is a **research prototype** and **proof-of-concept**. It is not production-ready and should not be used with sensitive data without proper security review. Use at your own risk.

**Known Limitations:**
- No authentication/authorization
- Limited error handling
- No data validation for malicious inputs
- CDC is experimental
- Performance not optimized for large datasets (>1M rows)
- LLM costs can add up quickly

---

<div align="center">

</div>


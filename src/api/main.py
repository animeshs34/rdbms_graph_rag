"""FastAPI application for RDBMS to Graph RAG system"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
from loguru import logger
import sys
from pathlib import Path

from ..config.settings import get_settings
from ..connectors.postgres import PostgreSQLConnector
from ..connectors.mysql import MySQLConnector
from ..connectors.sqlite import SQLiteConnector
from ..graph_db.neo4j_connector import Neo4jConnector
from ..schema_mapper.mapper import SchemaMapper
from ..schema_mapper.llm_enhancer import LLMSchemaEnhancer
from ..migration.migrator import DataMigrator
from ..embeddings.embedder import EmbeddingService
from ..embeddings.vector_store import VectorStore
from ..retrieval.agent import RetrievalAgent
from ..cdc.manager import CDCManager
from ..cdc.postgres_listener import PostgreSQLCDCListener
from ..cdc.handlers import GraphSyncHandler, EmbeddingSyncHandler

logger.remove()
logger.add(sys.stderr, level="INFO")

app = FastAPI(
    title="RDBMS to Graph RAG API",
    description="API for converting relational databases to knowledge graphs with intelligent retrieval",
    version="0.1.0"
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_path = Path(__file__).parent.parent / "web" / "static"
templates_path = Path(__file__).parent.parent / "web" / "templates"

if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

class DatabaseConfig(BaseModel):
    """Database configuration"""
    db_type: str
    connection_string: Optional[str] = None
    domain_prefix: Optional[str] = None  # e.g., "Ecommerce", "Healthcare"

class MigrationRequest(BaseModel):
    """Migration request"""
    db_type: str
    connection_string: Optional[str] = None
    target_graph_db: str = "neo4j"
    clear_target: bool = False
    domain_prefix: Optional[str] = None  # Prefix for node labels (e.g., "Ecommerce_", "Healthcare_")
    tables_filter: Optional[List[str]] = None
    
class QueryRequest(BaseModel):
    """Query request"""
    query: str
    top_k: int = 10
    
class SchemaResponse(BaseModel):
    """Schema response"""
    node_types: List[Dict[str, Any]]
    relationship_types: List[Dict[str, Any]]
    metadata: Dict[str, Any]


_graph_db = None
_embedding_service = None
_vector_store = None
_retrieval_agent = None
_cdc_manager = None
_current_graph_schema = None


def get_graph_db():
    """Get or create graph database connection"""
    global _graph_db
    if _graph_db is None:
        config = {
            "uri": settings.neo4j_uri,
            "user": settings.neo4j_user,
            "password": settings.neo4j_password
        }
        _graph_db = Neo4jConnector(config)
        _graph_db.connect()
    return _graph_db


def get_embedding_service():
    """Get or create embedding service"""
    global _embedding_service
    if _embedding_service is None:
        provider = settings.embedding_provider.lower()
        if provider == "gemini":
            api_key = settings.gemini_api_key
            model = settings.gemini_embedding_model
            dimension = 768
        else:
            api_key = settings.openai_api_key
            model = settings.openai_embedding_model
            dimension = 1536

        _embedding_service = EmbeddingService(
            api_key=api_key,
            model=model,
            provider=provider
        )
    return _embedding_service


def get_vector_store():
    """Get or create vector store"""
    global _vector_store
    if _vector_store is None:
        provider = settings.embedding_provider.lower()
        dimension = 768 if provider == "gemini" else 1536
        _vector_store = VectorStore(dimension=dimension)
    return _vector_store


def get_retrieval_agent():
    """Get or create retrieval agent"""
    global _retrieval_agent
    if _retrieval_agent is None:
        provider = settings.llm_provider.lower()
        if provider == "gemini":
            api_key = settings.gemini_api_key
            model = settings.gemini_model
        elif provider == "anthropic":
            api_key = settings.anthropic_api_key
            model = settings.llm_model
        else:
            api_key = settings.openai_api_key
            model = settings.openai_model

        _retrieval_agent = RetrievalAgent(
            graph_db=get_graph_db(),
            embedding_service=get_embedding_service(),
            vector_store=get_vector_store(),
            api_key=api_key,
            model=model,
            provider=provider
        )
    return _retrieval_agent


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI"""
    try:
        index_file = templates_path / "index.html"
        if index_file.exists():
            return index_file.read_text()
        else:
            return {
                "message": "RDBMS to Graph RAG API",
                "version": "0.1.0",
                "docs": "/docs"
            }
    except Exception as e:
        logger.error(f"Error serving UI: {e}")
        return {
            "message": "RDBMS to Graph RAG API",
            "version": "0.1.0",
            "docs": "/docs"
        }


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "RDBMS to Graph RAG API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/schema/map")
async def map_schema(config: DatabaseConfig) -> SchemaResponse:
    """
    Map a relational database schema to a graph schema
    
    Args:
        config: Database configuration
        
    Returns:
        Graph schema
    """
    try:
        if config.db_type == "postgres":
            connector = PostgreSQLConnector(config.connection_string or settings.postgres_url)
        elif config.db_type == "mysql":
            connector = MySQLConnector(config.connection_string or settings.mysql_url)
        elif config.db_type == "sqlite":
            connector = SQLiteConnector(config.connection_string or "./data/sample.db")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {config.db_type}")
        
        with connector:
            table_schemas = connector.get_all_schemas()

            llm_enhancer = None
            if settings.schema_llm_enabled:
                schema_provider = settings.schema_llm_provider.lower()
                if schema_provider == "gemini":
                    schema_api_key = settings.gemini_api_key
                else:
                    schema_api_key = settings.openai_api_key

                llm_enhancer = LLMSchemaEnhancer(
                    api_key=schema_api_key,
                    model=settings.schema_llm_model,
                    provider=schema_provider
                )

            mapper = SchemaMapper(llm_enhancer=llm_enhancer)
            graph_schema = mapper.map_schema(
                table_schemas,
                label_prefix=config.domain_prefix,
                source_connector=connector if llm_enhancer else None
            )
        
        return SchemaResponse(
            node_types=[nt.to_dict() for nt in graph_schema.node_types],
            relationship_types=[rt.to_dict() for rt in graph_schema.relationship_types],
            metadata=graph_schema.metadata
        )
        
    except Exception as e:
        logger.error(f"Error mapping schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/migrate")
async def migrate_data(request: MigrationRequest, background_tasks: BackgroundTasks):
    """
    Migrate data from RDBMS to graph database
    
    Args:
        request: Migration request
        background_tasks: FastAPI background tasks
        
    Returns:
        Migration status
    """
    try:
        connection_str = request.connection_string
        if request.db_type == "postgres":
            source = PostgreSQLConnector(connection_str or settings.postgres_url)
        elif request.db_type == "mysql":
            source = MySQLConnector(connection_str or settings.mysql_url)
        elif request.db_type == "sqlite":
            source = SQLiteConnector(connection_str or "./data/sample.db")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {request.db_type}")

        target = get_graph_db()

        with source:
            table_schemas = source.get_all_schemas()

            if request.tables_filter:
                table_schemas = {k: v for k, v in table_schemas.items() if k in request.tables_filter}
                logger.info(f"Filtered to {len(table_schemas)} tables: {list(table_schemas.keys())}")

            llm_enhancer = None
            if settings.schema_llm_enabled:
                schema_provider = settings.schema_llm_provider.lower()
                if schema_provider == "gemini":
                    schema_api_key = settings.gemini_api_key
                else:
                    schema_api_key = settings.openai_api_key

                llm_enhancer = LLMSchemaEnhancer(
                    api_key=schema_api_key,
                    model=settings.schema_llm_model,
                    provider=schema_provider
                )

            mapper = SchemaMapper(llm_enhancer=llm_enhancer)
            graph_schema = mapper.map_schema(
                table_schemas,
                label_prefix=request.domain_prefix,
                source_connector=source if llm_enhancer else None
            )

        with source:
            migrator = DataMigrator(source, target, graph_schema)
            stats = migrator.migrate(clear_target=request.clear_target)

        global _current_graph_schema
        _current_graph_schema = graph_schema

        return {
            "status": "completed",
            "nodes_created": stats.get("nodes_created", 0),
            "relationships_created": stats.get("relationships_created", 0),
            "domain_prefix": request.domain_prefix,
            "tables_migrated": list(table_schemas.keys())
        }
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query(request: QueryRequest) -> Dict[str, Any]:
    """
    Execute an intelligent query using the agentic retrieval system
    
    Args:
        request: Query request
        
    Returns:
        Query results and answer
    """
    try:
        agent = get_retrieval_agent()
        result = agent.query(request.query)
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Execute an intelligent query with streaming response

    Args:
        request: Query request

    Returns:
        Streaming response with progressive results
    """
    try:
        agent = get_retrieval_agent()

        async def generate():
            """Generate streaming response"""
            for chunk in agent.query_stream(request.query):
                yield json.dumps(chunk) + "\n"

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"Error executing streaming query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        graph_db = get_graph_db()

        node_types_query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) YIELD value
        RETURN label, value.count as count
        ORDER BY label
        """

        try:
            node_types_result = graph_db.execute_query(node_types_query)
            node_types = [{"label": r["label"], "count": r["count"]} for r in node_types_result]
        except:
            labels_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
            labels_result = graph_db.execute_query(labels_query)
            labels = labels_result[0]["labels"] if labels_result else []
            node_types = []
            for label in labels:
                count_query = f"MATCH (n:`{label}`) RETURN count(n) as count"
                count_result = graph_db.execute_query(count_query)
                node_types.append({"label": label, "count": count_result[0]["count"] if count_result else 0})

        rel_types_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        rel_types_result = graph_db.execute_query(rel_types_query)
        relationship_types = rel_types_result[0]["types"] if rel_types_result else []

        stats = {
            "total_nodes": graph_db.get_node_count(),
            "total_relationships": graph_db.get_relationship_count(),
            "node_types": node_types,
            "relationship_types": relationship_types,
            "vector_store_size": get_vector_store().size
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class EmbeddingRequest(BaseModel):
    """Embedding build request"""
    node_labels: Optional[List[str]] = None


@app.post("/embeddings/build")
async def build_embeddings(request: EmbeddingRequest, background_tasks: BackgroundTasks):
    """Build embeddings for all nodes in the graph"""
    try:
        graph_db = get_graph_db()
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()

        if request.node_labels:
            label_conditions = " OR ".join([f"n:`{label}`" for label in request.node_labels])
            query = f"MATCH (n) WHERE {label_conditions} RETURN n, labels(n) as labels LIMIT 1000"
        else:
            query = "MATCH (n) RETURN n, labels(n) as labels LIMIT 1000"

        nodes = graph_db.execute_query(query)

        vectors = []
        metadata_list = []

        for node_data in nodes:
            n = node_data.get("n", {})
            labels = node_data.get("labels", [])

            if hasattr(n, '_properties'):
                props = dict(n._properties)
            elif isinstance(n, dict):
                props = n
            else:
                props = {}

            text_parts = [f"Label: {', '.join(labels)}"]
            for key, value in props.items():
                if key not in ['id', 'created_at', 'updated_at']:
                    text_parts.append(f"{key}: {value}")

            text = ", ".join(text_parts)

            embedding = embedding_service.embed_text(text)
            vectors.append(embedding)

            metadata_list.append({
                "node_id": props.get("id", ""),
                "labels": labels,
                "text": text,
                "properties": props  # Now a plain dict, not a Neo4j Node
            })

        vector_store.add_vectors(vectors, metadata_list)

        return {
            "status": "completed",
            "embeddings_created": len(vectors),
            "vector_store_size": vector_store.size
        }

    except Exception as e:
        logger.error(f"Error building embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/embeddings/status")
async def get_embeddings_status():
    """Get status of the vector store"""
    try:
        vector_store = get_vector_store()
        status = vector_store.get_status()

        return {
            "status": "success",
            **status
        }
    except Exception as e:
        logger.error(f"Error getting embeddings status: {e}")
        raise HTTPException(status_code=500, detail=str(e))



class CDCSetupRequest(BaseModel):
    """CDC setup request"""
    db_type: str
    connection_string: Optional[str] = None
    domain_prefix: Optional[str] = None
    tables: Optional[List[str]] = None


class CDCControlRequest(BaseModel):
    """CDC control request"""
    action: str


@app.post("/cdc/setup")
async def setup_cdc(request: CDCSetupRequest):
    """Set up CDC for a database"""
    global _cdc_manager, _current_graph_schema

    try:
        if request.connection_string:
            conn_str = request.connection_string
        else:
            if request.db_type == "postgres":
                conn_str = settings.postgres_url
            elif request.db_type == "mysql":
                conn_str = settings.mysql_url
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported database type: {request.db_type}")

        if _cdc_manager is None:
            _cdc_manager = CDCManager(
                batch_size=settings.cdc_batch_size,
                batch_timeout=settings.cdc_batch_timeout,
                enable_batching=settings.cdc_enable_batching
            )

        if request.db_type == "postgres":
            from urllib.parse import urlparse
            parsed = urlparse(conn_str)

            connection_config = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password
            }

            listener = PostgreSQLCDCListener(
                connection_config=connection_config,
                slot_name=settings.postgres_cdc_slot_name,
                publication_name=settings.postgres_cdc_publication,
                tables=request.tables
            )

            listener_name = f"{request.db_type}_{request.domain_prefix or 'default'}"
            _cdc_manager.register_listener(listener_name, listener, auto_setup=True)

            if _current_graph_schema:
                graph_handler = GraphSyncHandler(
                    graph_db=get_graph_db(),
                    graph_schema=_current_graph_schema,
                    domain_prefix=request.domain_prefix or ""
                )
                _cdc_manager.add_handler(graph_handler)

                if settings.cdc_sync_embeddings:
                    embedding_handler = EmbeddingSyncHandler(
                        embedding_service=get_embedding_service(),
                        vector_store=get_vector_store(),
                        graph_schema=_current_graph_schema
                    )
                    _cdc_manager.add_handler(embedding_handler)

            return {
                "status": "success",
                "message": f"CDC set up for {request.db_type}",
                "listener_name": listener_name,
                "slot_name": settings.postgres_cdc_slot_name,
                "publication_name": settings.postgres_cdc_publication,
                "tables": request.tables or "all"
            }
        else:
            raise HTTPException(status_code=400, detail=f"CDC not yet implemented for {request.db_type}")

    except Exception as e:
        logger.error(f"Error setting up CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cdc/control")
async def control_cdc(request: CDCControlRequest):
    """Control CDC (start/stop/restart)"""
    global _cdc_manager

    if _cdc_manager is None:
        raise HTTPException(status_code=400, detail="CDC not set up. Call /cdc/setup first")

    try:
        if request.action == "start":
            _cdc_manager.start_all()
            return {"status": "success", "message": "CDC started"}

        elif request.action == "stop":
            _cdc_manager.stop_all()
            return {"status": "success", "message": "CDC stopped"}

        elif request.action == "restart":
            _cdc_manager.stop_all()
            _cdc_manager.start_all()
            return {"status": "success", "message": "CDC restarted"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    except Exception as e:
        logger.error(f"Error controlling CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cdc/status")
async def get_cdc_status():
    """Get CDC status"""
    global _cdc_manager

    if _cdc_manager is None:
        return {
            "status": "not_configured",
            "message": "CDC not set up"
        }

    try:
        status = _cdc_manager.get_status()
        return {
            "status": "success",
            **status
        }
    except Exception as e:
        logger.error(f"Error getting CDC status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cdc/cleanup")
async def cleanup_cdc():
    """Clean up CDC resources (replication slots, publications, etc.)"""
    global _cdc_manager

    if _cdc_manager is None:
        raise HTTPException(status_code=400, detail="CDC not set up")

    try:
        _cdc_manager.stop_all()
        _cdc_manager.cleanup_all()
        _cdc_manager = None

        return {
            "status": "success",
            "message": "CDC resources cleaned up"
        }
    except Exception as e:
        logger.error(f"Error cleaning up CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, reload=settings.api_reload)


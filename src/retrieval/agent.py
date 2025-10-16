"""LangGraph-based agentic retrieval system"""

from typing import Dict, Any, List, Annotated
from typing_extensions import TypedDict
import operator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from loguru import logger

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    ChatGoogleGenerativeAI = None

from ..graph_db.base import GraphDatabaseConnector
from ..embeddings.embedder import EmbeddingService
from ..embeddings.vector_store import VectorStore
from .query_processor import QueryProcessor


class AgentState(TypedDict):
    """State for the retrieval agent"""
    query: str
    expanded_queries: List[str]
    intent: str
    entities: Dict[str, List[str]]
    cypher_query: str
    graph_results: List[Dict[str, Any]]
    vector_results: List[Dict[str, Any]]
    combined_results: List[Dict[str, Any]]
    context: str
    answer: str
    messages: Annotated[List, operator.add]
    iteration: int


class RetrievalAgent:
    """Agentic retrieval system using LangGraph"""
    
    def __init__(
        self,
        graph_db: GraphDatabaseConnector,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        provider: str = "openai",
        max_iterations: int = 5
    ):
        """
        Initialize retrieval agent

        Args:
            graph_db: Graph database connector
            embedding_service: Embedding service
            vector_store: Vector store for similarity search
            api_key: LLM provider API key
            model: LLM model to use
            provider: LLM provider ('openai' or 'gemini')
            max_iterations: Maximum number of iterations
        """
        self.graph_db = graph_db
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.provider = provider.lower()
        self.query_processor = QueryProcessor(api_key, model, provider)

        if self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError(
                    "Gemini provider requested but langchain-google-genai is not installed. "
                    "Install it with: pip install langchain-google-genai"
                )
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=api_key,
                model=model,
                temperature=0.0
            )
        else:
            self.llm = ChatOpenAI(api_key=api_key, model=model, temperature=0.0)

        self.max_iterations = max_iterations
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        workflow.add_node("process_query", self._process_query)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("generate_answer", self._generate_answer)
        workflow.add_node("reflect", self._reflect)

        workflow.set_entry_point("process_query")
        workflow.add_edge("process_query", "retrieve")
        workflow.add_edge("retrieve", "generate_answer")
        workflow.add_conditional_edges(
            "generate_answer",
            self._should_continue,
            {
                "reflect": "reflect",
                "end": END
            }
        )
        workflow.add_edge("reflect", "process_query")

        return workflow.compile()
    
    def _process_query(self, state: AgentState) -> AgentState:
        """Process and expand the user query with parallel LLM calls"""
        logger.info(f"Processing query: {state['query']}")

        expanded, entities, intent = self.query_processor.process_query_parallel(state["query"])

        schema_info = self._get_schema_info()
        cypher = self.query_processor.generate_cypher_query(state["query"], schema_info)

        return {
            **state,
            "expanded_queries": expanded,
            "entities": entities,
            "intent": intent,
            "cypher_query": cypher,
            "messages": [HumanMessage(content=f"Processing query: {state['query']}")],
            "iteration": state.get("iteration", 0) + 1
        }
    
    def _retrieve(self, state: AgentState) -> AgentState:
        """Perform both vector and graph retrieval"""
        logger.info("Performing retrieval")

        vector_results = []
        graph_results = []

        try:
            if self.vector_store.size > 0:
                for query in state["expanded_queries"][:3]:  # Limit to top 3
                    query_embedding = self.embedding_service.embed_text(query)

                    similar = self.vector_store.search(query_embedding, top_k=5)

                    for metadata, distance in similar:
                        vector_results.append({
                            "source": "vector",
                            "query": query,
                            "data": metadata,
                            "score": 1.0 / (1.0 + distance)  # Convert distance to similarity
                        })

                logger.info(f"Found {len(vector_results)} vector search results")
            else:
                logger.warning("Vector store is empty, skipping vector search")
        except Exception as e:
            logger.error(f"Error in vector search: {e}")

        if state.get("cypher_query"):
            try:
                graph_data = self.graph_db.execute_query(state["cypher_query"])

                for result in graph_data:
                    serializable_result = self._serialize_neo4j_result(result)
                    graph_results.append({
                        "source": "graph",
                        "data": serializable_result,
                        "score": 1.0
                    })

                logger.info(f"Graph query returned {len(graph_results)} results")
            except Exception as e:
                logger.error(f"Error executing graph query: {e}")

        all_results = vector_results + graph_results
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        combined = all_results[:10]

        context_parts = []
        seen_data = set()

        for i, result in enumerate(combined, 1):
            data = result['data']
            data_str = str(data)
            if data_str not in seen_data:
                seen_data.add(data_str)
                if isinstance(data, dict):
                    formatted_data = self._format_result_data(data)
                    context_parts.append(f"Result {len(context_parts) + 1}: {formatted_data}")
                else:
                    context_parts.append(f"Result {len(context_parts) + 1}: {data}")

        context = "\n\n".join(context_parts)

        return {
            **state,
            "vector_results": vector_results,
            "graph_results": graph_results,
            "combined_results": combined,
            "context": context,
            "messages": [AIMessage(content=f"Retrieved {len(combined)} total results")]
        }
    
    def _generate_answer(self, state: AgentState) -> AgentState:
        """Generate final answer using LLM"""
        logger.info("Generating answer")

        query_lower = state['query'].lower()
        is_count_query = any(word in query_lower for word in ['how many', 'count', 'number of', 'total'])
        is_list_query = any(word in query_lower for word in ['list', 'show', 'what', 'which', 'all'])
        is_overview_query = any(word in query_lower for word in ['what data', 'what information', 'overview', 'summary'])

        if is_overview_query:
            prompt = f"""You are analyzing a healthcare database. The user asked: "{state['query']}"

Context from database (ONLY use this information, do NOT make up numbers):
{state['context']}

Analyze the context and provide a CONCISE overview. Format your response as:

**Available Data Types:**
List the types of entities you see (Patients, Doctors, Departments, etc.)

**Sample Data:**
Briefly mention a few examples from the context

**Important:**
- ONLY use information from the context provided
- Do NOT invent statistics or numbers
- If you see limited data, say "Sample data includes..." instead of claiming totals
- Keep it brief and factual"""

        elif is_count_query:
            prompt = f"""Answer this counting question concisely: "{state['query']}"

Context:
{state['context']}

Provide a SHORT, DIRECT answer. Format:
- Start with the number/count
- Add 1-2 sentences of relevant detail if helpful
- Do NOT repeat information

Example: "There are 12 appointments scheduled. This includes appointments across all departments from January to March 2024." """

        elif is_list_query:
            prompt = f"""Answer this listing question: "{state['query']}"

Context:
{state['context']}

Format your response as:
1. Brief introduction (1 sentence)
2. Bulleted or numbered list of items
3. Each item: key information only (name, role, key details)

Keep it concise. Avoid repeating the same information. Group similar items if appropriate."""

        else:
            prompt = f"""Answer this question based on the healthcare database: "{state['query']}"

Context:
{state['context']}

Provide a CLEAR, CONCISE answer:
- Start with the direct answer
- Add relevant supporting details
- Use bullet points or short paragraphs
- Avoid repetition
- If information is missing, state it briefly"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            answer = response.content
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            answer = "I encountered an error while generating the answer."

        return {
            **state,
            "answer": answer,
            "messages": [AIMessage(content=f"Generated answer")]
        }
    
    def _reflect(self, state: AgentState) -> AgentState:
        """Reflect on the answer quality and decide if refinement is needed"""
        logger.info("Reflecting on answer quality")
        
        answer = state.get("answer", "")
        
        if len(answer) < 50 or "don't have enough information" in answer.lower():
            refined_query = f"{state['query']} (provide more details)"
            return {
                **state,
                "query": refined_query,
                "messages": [AIMessage(content="Refining query for better results")]
            }
        
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue iterating or end"""
        iteration = state.get("iteration", 0)
        answer = state.get("answer", "")

        return "end"

        if iteration >= self.max_iterations:
            return "end"

        if len(answer) > 50 and "don't have enough information" not in answer.lower():
            return "end"

        if iteration < 2 and len(state.get("results", [])) == 0:
            return "reflect"

        return "end"
    
    def _format_result_data(self, data: dict) -> str:
        """Format result data in a clean, readable way"""
        formatted_parts = []

        for key, value in data.items():
            if isinstance(value, dict):
                if '_labels' in value:
                    labels = value.get('_labels', [])
                    props = {k: v for k, v in value.items() if not k.startswith('_')}

                    name_fields = ['name', 'first_name', 'last_name', 'title']
                    name_parts = []
                    for field in name_fields:
                        if field in props:
                            name_parts.append(str(props[field]))

                    if name_parts:
                        formatted_parts.append(f"{key}: {' '.join(name_parts)} ({', '.join(labels)})")
                    else:
                        formatted_parts.append(f"{key}: {labels[0] if labels else 'Node'}")

                    important_fields = ['id', 'email', 'phone', 'specialization', 'department_id', 'diagnosis']
                    for field in important_fields:
                        if field in props and field not in name_fields:
                            formatted_parts.append(f"  - {field}: {props[field]}")
                else:
                    formatted_parts.append(f"{key}: {value}")
            else:
                formatted_parts.append(f"{key}: {value}")

        return ", ".join(formatted_parts) if formatted_parts else str(data)

    def _serialize_neo4j_result(self, result):
        """Convert Neo4j objects to serializable dictionaries"""
        if isinstance(result, dict):
            serialized = {}
            for key, value in result.items():
                if hasattr(value, '__class__') and 'neo4j' in str(value.__class__):
                    if hasattr(value, '_properties'):
                        serialized[key] = dict(value._properties)
                        if hasattr(value, 'labels'):
                            serialized[key]['_labels'] = list(value.labels)
                        if hasattr(value, 'id'):
                            serialized[key]['_id'] = value.id
                    else:
                        serialized[key] = str(value)
                elif isinstance(value, (list, tuple)):
                    serialized[key] = [self._serialize_neo4j_result(item) for item in value]
                elif isinstance(value, dict):
                    serialized[key] = self._serialize_neo4j_result(value)
                else:
                    serialized[key] = value
            return serialized
        elif hasattr(result, '__class__') and 'neo4j' in str(result.__class__):
            if hasattr(result, '_properties'):
                data = dict(result._properties)
                if hasattr(result, 'labels'):
                    data['_labels'] = list(result.labels)
                if hasattr(result, 'id'):
                    data['_id'] = result.id
                return data
            else:
                return str(result)
        elif isinstance(result, (list, tuple)):
            return [self._serialize_neo4j_result(item) for item in result]
        else:
            return result

    def _get_schema_info(self) -> str:
        """Get graph schema information for query generation"""
        try:
            labels_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
            labels_result = self.graph_db.execute_query(labels_query)
            labels = labels_result[0]["labels"] if labels_result else []

            rel_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
            rel_result = self.graph_db.execute_query(rel_query)
            rel_types = rel_result[0]["types"] if rel_result else []

            node_info = []
            for label in labels[:10]:
                try:
                    prop_query = f"MATCH (n:`{label}`) RETURN keys(n) as props LIMIT 1"
                    prop_result = self.graph_db.execute_query(prop_query)
                    if prop_result:
                        props = prop_result[0].get("props", [])
                        node_info.append(f"  - {label}: {', '.join(props[:10])}")
                except:
                    node_info.append(f"  - {label}")

            schema = f"""
Graph Schema:
- Node types: {', '.join(labels)}
- Relationships: {', '.join(rel_types)}

Node Details:
{chr(10).join(node_info)}

Example Cypher patterns:
- Find nodes: MATCH (n:Label) WHERE n.property = 'value' RETURN n
- Follow relationships: MATCH (a)-[r:REL_TYPE]->(b) RETURN a, r, b
- Aggregations: MATCH (n:Label) RETURN count(n)
"""
            return schema
        except Exception as e:
            logger.error(f"Error getting schema: {e}")
            return "Graph Schema: Unable to retrieve schema"
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Execute a query through the agent
        
        Args:
            user_query: User's natural language query
            
        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Agent received query: {user_query}")
        
        initial_state = {
            "query": user_query,
            "expanded_queries": [],
            "intent": "",
            "entities": {},
            "cypher_query": "",
            "graph_results": [],
            "vector_results": [],
            "combined_results": [],
            "context": "",
            "answer": "",
            "messages": [],
            "iteration": 0
        }
        
        final_state = self.graph.invoke(initial_state)
        
        return {
            "query": user_query,
            "answer": final_state.get("answer", ""),
            "context": final_state.get("context", ""),
            "results": final_state.get("combined_results", []),
            "iterations": final_state.get("iteration", 0),
            "intent": final_state.get("intent", ""),
            "entities": final_state.get("entities", {})
        }

    def query_stream(self, user_query: str):
        """
        Execute a query and stream the response

        Args:
            user_query: User's natural language query

        Yields:
            Dictionary chunks with progressive results
        """
        logger.info(f"Agent received streaming query: {user_query}")

        yield {
            "type": "status",
            "message": "Processing query...",
            "query": user_query
        }

        initial_state = {
            "query": user_query,
            "expanded_queries": [],
            "intent": "",
            "entities": {},
            "cypher_query": "",
            "graph_results": [],
            "vector_results": [],
            "combined_results": [],
            "context": "",
            "answer": "",
            "messages": [],
            "iteration": 0
        }

        yield {
            "type": "status",
            "message": "Analyzing query..."
        }

        state = self._process_query(initial_state)

        yield {
            "type": "query_analysis",
            "expanded_queries": state["expanded_queries"],
            "entities": state["entities"],
            "intent": state["intent"]
        }

        yield {
            "type": "status",
            "message": "Retrieving data..."
        }

        state = self._retrieve(state)

        yield {
            "type": "retrieval",
            "graph_results_count": len(state.get("graph_results", [])),
            "vector_results_count": len(state.get("vector_results", [])),
            "cypher_query": state.get("cypher_query", "")
        }

        yield {
            "type": "status",
            "message": "Generating answer..."
        }

        context = state.get("context", "")

        prompt = f"""Based on the following context from a knowledge graph, answer the user's question.

Context:
{context}

Question: {user_query}

Provide a clear, comprehensive answer based on the context. If the context doesn't contain enough information, say so."""

        answer_chunks = []
        try:
            stream = self.llm.stream([HumanMessage(content=prompt)])

            for chunk in stream:
                if hasattr(chunk, 'content') and chunk.content:
                    answer_chunks.append(chunk.content)
                    yield {
                        "type": "answer_chunk",
                        "content": chunk.content
                    }
        except Exception as e:
            logger.error(f"Error streaming answer: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }

        full_answer = "".join(answer_chunks)
        yield {
            "type": "complete",
            "query": user_query,
            "answer": full_answer,
            "context": context,
            "results": state.get("combined_results", []),
            "iterations": state.get("iteration", 0),
            "intent": state.get("intent", ""),
            "entities": state.get("entities", {})
        }


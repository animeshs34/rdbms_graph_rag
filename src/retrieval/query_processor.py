"""Query processing and expansion"""

from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from ..llm.provider import create_llm_provider, LLMProvider


class QueryProcessor:
    """Processes and expands user queries for better retrieval"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        provider: str = "openai"
    ):
        """
        Initialize query processor

        Args:
            api_key: LLM provider API key
            model: LLM model to use
            provider: LLM provider ('openai' or 'gemini')
        """
        self.provider = create_llm_provider(provider, api_key, model)
        self.model = model
        self.provider_name = provider
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand a query into multiple related queries
        
        Args:
            query: Original user query
            
        Returns:
            List of expanded queries
        """
        prompt = f"""Given the following query, generate exactly 2 alternative queries that would help retrieve comprehensive information.

Original Query: {query}

Generate queries that:
1. Rephrase the original query with different wording
2. Add related context or synonyms

Return only the 2 queries, one per line. Be concise."""

        try:
            response = self.provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            expanded = response.strip().split('\n')
            expanded = [q.strip() for q in expanded if q.strip()]

            if query not in expanded:
                expanded.insert(0, query)

            logger.info(f"Expanded query into {len(expanded)} queries")
            return expanded
            
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return [query]
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities from a query

        Args:
            query: User query

        Returns:
            Dictionary of entity types to entity values
        """
        import json

        prompt = f"""Extract entities from the following query and categorize them.

Query: {query}

Extract:
- People/Organizations
- Locations
- Dates/Times
- Products/Items
- Concepts/Topics

Return ONLY valid JSON with categories as keys and lists of entities as values.
Example: {{"people": ["John"], "locations": ["New York"], "dates": [], "products": [], "concepts": []}}"""

        response = ""
        try:
            response = self.provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            # Clean response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Check if response is empty or not JSON
            if not response or response == "":
                logger.warning(f"Empty response from LLM for entity extraction")
                return {}

            entities = json.loads(response)
            logger.info(f"Extracted entities: {entities}")
            return entities

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}. Response was: {response[:200] if response else 'N/A'}")
            return {}
        except Exception as e:
            logger.warning(f"Error extracting entities: {e}")
            return {}
    
    def generate_cypher_query(self, natural_language_query: str, schema_info: str) -> str:
        """
        Generate a Cypher query from natural language
        
        Args:
            natural_language_query: User's natural language query
            schema_info: Graph schema information
            
        Returns:
            Cypher query string
        """
        prompt = f"""Given the following graph schema and natural language query, generate a Cypher query.

Schema:
{schema_info}

Natural Language Query: {natural_language_query}

Generate a valid Cypher query that answers the question. Return only the Cypher query, no explanation."""

        try:
            response = self.provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )

            cypher = response.strip()
            if cypher.startswith("```"):
                cypher = cypher.split("```")[1]
                if cypher.startswith("cypher"):
                    cypher = cypher[6:]
                cypher = cypher.strip()

            logger.info(f"Generated Cypher query: {cypher}")
            return cypher
            
        except Exception as e:
            logger.error(f"Error generating Cypher query: {e}")
            return ""
    
    def classify_query_intent(self, query: str) -> str:
        """
        Classify the intent of a query
        
        Args:
            query: User query
            
        Returns:
            Query intent (e.g., 'search', 'aggregate', 'relationship', 'comparison')
        """
        prompt = f"""Classify the intent of the following query into one of these categories:
- search: Looking for specific entities or information
- aggregate: Counting, summing, or aggregating data
- relationship: Finding connections or relationships between entities
- comparison: Comparing entities or values
- temporal: Time-based queries

Query: {query}

Return only the category name."""

        try:
            response = self.provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )

            intent = response.strip().lower()
            logger.info(f"Query intent: {intent}")
            return intent
            
        except Exception as e:
            logger.error(f"Error classifying query intent: {e}")
            return "search"

    def process_query_parallel(self, query: str) -> Tuple[List[str], Dict[str, List[str]], str]:
        """
        Process query with parallel LLM calls for expansion, entity extraction, and intent classification

        Args:
            query: User query

        Returns:
            Tuple of (expanded_queries, entities, intent)
        """
        logger.info("Processing query with parallel LLM calls")

        expanded_queries = [query]
        entities = {}
        intent = "search"

        def expand():
            return self.expand_query(query)

        def extract():
            return self.extract_entities(query)

        def classify():
            return self.classify_query_intent(query)

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_expand = executor.submit(expand)
            future_extract = executor.submit(extract)
            future_classify = executor.submit(classify)

            expanded_queries = future_expand.result()
            entities = future_extract.result()
            intent = future_classify.result()

        logger.info(f"Parallel processing complete: {len(expanded_queries)} queries, {sum(len(v) for v in entities.values())} entities, intent={intent}")
        return expanded_queries, entities, intent


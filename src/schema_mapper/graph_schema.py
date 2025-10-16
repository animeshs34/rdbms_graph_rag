"""Graph schema data structures"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class PropertyType(Enum):
    """Graph property types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"


@dataclass
class Property:
    """Represents a property in a graph node or relationship"""
    name: str
    type: PropertyType
    required: bool = False
    indexed: bool = False
    unique: bool = False
    description: Optional[str] = None


@dataclass
class NodeType:
    """Represents a node type in the graph schema"""
    label: str
    properties: List[Property] = field(default_factory=list)
    source_table: Optional[str] = None
    primary_key: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "label": self.label,
            "properties": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "indexed": p.indexed,
                    "unique": p.unique,
                    "description": p.description
                }
                for p in self.properties
            ],
            "source_table": self.source_table,
            "primary_key": self.primary_key,
            "description": self.description
        }


@dataclass
class RelationshipType:
    """Represents a relationship type in the graph schema"""
    type: str
    from_node: str
    to_node: str
    properties: List[Property] = field(default_factory=list)
    source_foreign_key: Optional[Dict[str, str]] = None
    cardinality: str = "many-to-one"  # one-to-one, one-to-many, many-to-one, many-to-many
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "type": self.type,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "properties": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "indexed": p.indexed
                }
                for p in self.properties
            ],
            "source_foreign_key": self.source_foreign_key,
            "cardinality": self.cardinality,
            "description": self.description
        }


@dataclass
class GraphSchema:
    """Represents a complete graph schema"""
    node_types: List[NodeType] = field(default_factory=list)
    relationship_types: List[RelationshipType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_node_type(self, node_type: NodeType) -> None:
        """Add a node type to the schema"""
        self.node_types.append(node_type)
    
    def add_relationship_type(self, relationship_type: RelationshipType) -> None:
        """Add a relationship type to the schema"""
        self.relationship_types.append(relationship_type)
    
    def get_node_type(self, label: str) -> Optional[NodeType]:
        """Get a node type by label"""
        for node_type in self.node_types:
            if node_type.label == label:
                return node_type
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "node_types": [nt.to_dict() for nt in self.node_types],
            "relationship_types": [rt.to_dict() for rt in self.relationship_types],
            "metadata": self.metadata
        }


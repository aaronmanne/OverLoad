"""
Document Storage Manager
Handles storage and retrieval of generated adversarial documents.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid


class DocumentStore:
    """In-memory document storage with metadata tracking."""
    
    def __init__(self):
        """Initialize the document store."""
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.payloads: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    
    def create_document(self, config: Dict[str, Any]) -> str:
        """
        Create and store a new document.
        
        Args:
            config: Document configuration dictionary with keys:
                - strategy: str
                - size_kb: int
                - aggression: int
                - doc_category: Optional[str]
                - jailbreak_techniques: Optional[List[str]]
        
        Returns:
            Document ID
        """
        doc_id = str(uuid.uuid4())[:8]
        
        # Extract config
        strategy = config.get('strategy', 'adversarial')
        size_kb = config.get('size_kb', 512)
        aggression = config.get('aggression', 2)
        doc_category = config.get('doc_category')
        jailbreak_techniques = config.get('jailbreak_techniques', [])
        
        # Expand jailbreak techniques
        expanded_techniques = self._expand_techniques(jailbreak_techniques)
        
        # Store metadata
        metadata = {
            "id": doc_id,
            "strategy": strategy,
            "size_kb": size_kb,
            "aggression": aggression,
            "doc_category": doc_category,
            "jailbreak_techniques": expanded_techniques,
            "jailbreak_count": len(expanded_techniques),
            "created_at": datetime.utcnow().isoformat(),
            "doc_title": self._get_category_title(doc_category)
        }
        
        self.documents[doc_id] = metadata
        
        return doc_id
    
    def store_payload(self, doc_id: str, html: str, 
                     metadata: Dict[str, Any]) -> None:
        """
        Store the generated HTML payload for a document.
        
        Args:
            doc_id: Document ID
            html: Generated HTML content
            metadata: Payload metadata (title, breadcrumb, etc.)
        """
        self.payloads[doc_id] = (html, metadata)
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document metadata.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document metadata or None if not found
        """
        return self.documents.get(doc_id)
    
    def get_payload(self, doc_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Retrieve document payload.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Tuple of (HTML content, metadata) or None if not found
        """
        return self.payloads.get(doc_id)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all documents.
        
        Returns:
            List of document metadata dictionaries
        """
        return sorted(
            self.documents.values(),
            key=lambda d: d.get('created_at', ''),
            reverse=True
        )
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete a document and its payload.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted, False if not found
        """
        found = False
        
        if doc_id in self.documents:
            del self.documents[doc_id]
            found = True
        
        if doc_id in self.payloads:
            del self.payloads[doc_id]
            found = True
        
        return found
    
    def clear_all(self) -> int:
        """
        Clear all documents.
        
        Returns:
            Number of documents cleared
        """
        count = len(self.documents)
        self.documents.clear()
        self.payloads.clear()
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Statistics dictionary
        """
        total_jailbreaks = sum(
            doc.get('jailbreak_count', 0) 
            for doc in self.documents.values()
        )
        
        strategies = {}
        for doc in self.documents.values():
            strategy = doc.get('strategy', 'unknown')
            strategies[strategy] = strategies.get(strategy, 0) + 1
        
        return {
            "total_documents": len(self.documents),
            "total_payloads": len(self.payloads),
            "total_jailbreaks": total_jailbreaks,
            "strategies": strategies
        }
    
    @staticmethod
    def _expand_techniques(techniques: List[str]) -> List[str]:
        """
        Expand technique categories into individual techniques.
        
        Args:
            techniques: List of technique categories or 'all'
            
        Returns:
            Expanded list of individual techniques
        """
        # Import here to avoid circular dependency
        from payload_generator import JAILBREAK_CATEGORIES
        
        if not techniques or 'all' in techniques:
            # Return all techniques from all categories
            all_techniques = []
            for category_techniques in JAILBREAK_CATEGORIES.values():
                all_techniques.extend(category_techniques)
            return all_techniques
        
        expanded = []
        for item in techniques:
            if item in JAILBREAK_CATEGORIES:
                # It's a category - add all techniques from that category
                expanded.extend(JAILBREAK_CATEGORIES[item])
            else:
                # It's an individual technique
                expanded.append(item)
        
        return expanded
    
    @staticmethod
    def _get_category_title(category: Optional[str]) -> str:
        """
        Get display title for a document category.
        
        Args:
            category: Document category ID
            
        Returns:
            Human-readable title
        """
        from payload_generator import DOCUMENT_CATEGORIES
        
        if not category:
            return "Technical Document"
        
        cat_info = DOCUMENT_CATEGORIES.get(category, {})
        return cat_info.get('title', category.replace('_', ' ').title())

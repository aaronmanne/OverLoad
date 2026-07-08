"""
Route Handlers for OverLoad Application
Organized, object-oriented route management.
"""

from typing import Tuple, Dict, Any
from flask import jsonify, request, Response
from template_manager import TemplateManager
import json


class RouteHandler:
    """Base class for route handlers."""
    
    def __init__(self, template_manager: TemplateManager):
        """
        Initialize the route handler.
        
        Args:
            template_manager: TemplateManager instance for rendering templates
        """
        self.template_manager = template_manager


class DashboardHandler(RouteHandler):
    """Handles the main dashboard page."""
    
    def get(self) -> str:
        """
        Render the main dashboard.
        
        Returns:
            Rendered dashboard HTML
        """
        return self.template_manager.render_dashboard()


class PayloadHandler(RouteHandler):
    """Handles payload document serving."""
    
    def __init__(self, template_manager: TemplateManager, payload_generator):
        """
        Initialize payload handler.
        
        Args:
            template_manager: TemplateManager instance
            payload_generator: Payload generation module/class
        """
        super().__init__(template_manager)
        self.payload_generator = payload_generator
    
    def get(self, doc_id: str = None, metadata: Dict[str, Any] = None,
            content_html: str = None) -> str:
        """
        Serve a payload document.
        
        Args:
            doc_id: Document ID
            metadata: Document metadata dictionary
            content_html: Pre-rendered content HTML
            
        Returns:
            Rendered payload HTML
        """
        # If metadata and content provided, use them directly
        if metadata and content_html:
            return self.template_manager.render_payload(
                doc_title=metadata.get('title', 'Document'),
                breadcrumb=metadata.get('breadcrumb', ''),
                content_html=content_html
            )
        
        # Otherwise, this would retrieve from storage
        raise NotImplementedError("Document retrieval not implemented")


class VisitsHandler(RouteHandler):
    """Handles the visits log page."""
    
    def __init__(self, template_manager: TemplateManager, visit_logger):
        """
        Initialize visits handler.
        
        Args:
            template_manager: TemplateManager instance
            visit_logger: Visit logging system
        """
        super().__init__(template_manager)
        self.visit_logger = visit_logger
    
    def get(self) -> str:
        """
        Render the visits log page.
        
        Returns:
            Rendered visits HTML
        """
        visits = self.visit_logger.get_all_visits()
        visits_json = json.dumps(visits, indent=2, default=str)
        return self.template_manager.render_visits(visits_json=visits_json)


class TestHandler(RouteHandler):
    """Handles the interactive Ollama testing page."""
    
    def get(self) -> str:
        """
        Render the interactive testing page.
        
        Returns:
            Rendered test HTML
        """
        return self.template_manager.render_test()


class APIHandler:
    """Handles API endpoints."""
    
    def __init__(self, document_store, llm_profiles, ollama_client):
        """
        Initialize API handler.
        
        Args:
            document_store: Document storage system
            llm_profiles: LLM profiles configuration
            ollama_client: Ollama integration client
        """
        self.document_store = document_store
        self.llm_profiles = llm_profiles
        self.ollama_client = ollama_client
    
    def generate_document(self) -> Tuple[Dict[str, Any], int]:
        """
        Generate a new adversarial document.
        
        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            
            # Validate required fields
            strategy = data.get('strategy', 'adversarial')
            size_kb = data.get('size_kb', 512)
            
            # Generate document (implementation would call actual generator)
            # For now, this is a placeholder
            doc_id = self.document_store.create_document(data)
            
            return {
                "id": doc_id,
                "strategy": strategy,
                "size_kb": size_kb,
                "jailbreak_count": len(data.get('jailbreak_techniques', []))
            }, 201
            
        except Exception as e:
            return {"error": str(e)}, 500
    
    def list_documents(self) -> Tuple[list, int]:
        """
        List all generated documents.
        
        Returns:
            Tuple of (document list, HTTP status code)
        """
        documents = self.document_store.list_all()
        return documents, 200
    
    def delete_document(self, doc_id: str) -> Tuple[Dict[str, str], int]:
        """
        Delete a document.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            Tuple of (JSON response, HTTP status code)
        """
        if self.document_store.delete(doc_id):
            return {"status": "deleted"}, 200
        return {"error": "Document not found"}, 404
    
    def get_llm_profiles(self) -> Tuple[Dict[str, Any], int]:
        """
        Get LLM profile configurations.
        
        Returns:
            Tuple of (profiles dict, HTTP status code)
        """
        return self.llm_profiles, 200
    
    def ollama_status(self) -> Tuple[Dict[str, Any], int]:
        """
        Check Ollama service status.
        
        Returns:
            Tuple of (status dict, HTTP status code)
        """
        status = self.ollama_client.check_status()
        return status, 200
    
    def ollama_models(self) -> Tuple[Dict[str, Any], int]:
        """
        List available Ollama models.
        
        Returns:
            Tuple of (models dict, HTTP status code)
        """
        models = self.ollama_client.list_models()
        return models, 200
    
    def ollama_chat(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle Ollama chat request.
        
        Returns:
            Tuple of (response dict, HTTP status code)
        """
        try:
            data = request.get_json()
            if not data:
                return {"error": "No JSON data provided"}, 400
            
            session_id = data.get('session_id')
            model = data.get('model')
            message = data.get('message')
            system = data.get('system')
            
            if not all([session_id, model, message]):
                return {"error": "Missing required fields"}, 400
            
            response = self.ollama_client.send_message(
                session_id=session_id,
                model=model,
                message=message,
                system=system
            )
            
            return response, 200
            
        except Exception as e:
            return {"error": str(e)}, 500
    
    def ollama_history(self, session_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Get conversation history.
        
        Args:
            session_id: Session ID
            
        Returns:
            Tuple of (history dict, HTTP status code)
        """
        history = self.ollama_client.get_history(session_id)
        if history:
            return history, 200
        return {"error": "Session not found"}, 404
    
    def ollama_clear_history(self, session_id: str) -> Tuple[Dict[str, str], int]:
        """
        Clear conversation history.
        
        Args:
            session_id: Session ID
            
        Returns:
            Tuple of (status dict, HTTP status code)
        """
        if self.ollama_client.clear_history(session_id):
            return {"status": "cleared"}, 200
        return {"status": "not_found"}, 404


class HealthCheckHandler:
    """Handles health check endpoints."""
    
    @staticmethod
    def ping() -> Dict[str, str]:
        """
        Simple health check.
        
        Returns:
            Status dictionary
        """
        return {"status": "ok"}

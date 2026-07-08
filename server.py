"""
Flask web server for OverLoad - Refactored and Object-Oriented
"""

import os
import time
from flask import Flask, request, jsonify

# Import object-oriented components
from template_manager import TemplateManager
from routes import (
    DashboardHandler, PayloadHandler, VisitsHandler, TestHandler,
    APIHandler, HealthCheckHandler
)
from ollama_client import OllamaClient
from document_store import DocumentStore
from visit_logger import VisitLogger
from payload_generator import generate_payload
from llm_profiles import LLM_PROFILES

# ---------------------------------------------------------------------------
# Application Setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.template_folder = 'templates'

# Initialize components
template_manager = TemplateManager()
ollama_client = OllamaClient()
document_store = DocumentStore()
visit_logger = VisitLogger()

# Initialize handlers
dashboard_handler = DashboardHandler(template_manager)
payload_handler = PayloadHandler(template_manager, generate_payload)
visits_handler = VisitsHandler(template_manager, visit_logger)
test_handler = TestHandler(template_manager)
api_handler = APIHandler(document_store, LLM_PROFILES, ollama_client)
health_handler = HealthCheckHandler()


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------

@app.before_request
def log_request():
    """Log incoming requests."""
    request.start_time = time.time()


@app.after_request
def log_response(response):
    """Log request completion and track visits."""
    if hasattr(request, 'start_time'):
        elapsed_ms = (time.time() - request.start_time) * 1000
        
        # Log document accesses
        if request.path.startswith('/doc') or request.path == '/document':
            visit_logger.log_visit(
                route=request.path,
                ip=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                referer=request.headers.get('Referer'),
                elapsed_ms=elapsed_ms
            )
    
    return response


# ---------------------------------------------------------------------------
# Web Routes
# ---------------------------------------------------------------------------

@app.get("/")
def dashboard():
    """Main dashboard page."""
    return dashboard_handler.get()


@app.get("/visits")
def visits_log():
    """Visits log page."""
    return visits_handler.get()


@app.get("/test")
def interactive_test():
    """Interactive Ollama testing page."""
    return test_handler.get()


@app.get("/ping")
def ping():
    """Health check endpoint."""
    return health_handler.ping()


@app.get("/document")
@app.get("/document/<int:example_number>")
@app.get("/doc/<doc_id>")
def serve_document(example_number=None, doc_id=None):
    """Serve adversarial payload documents."""
    
    # If doc_id provided, serve from store
    if doc_id:
        payload_data = document_store.get_payload(doc_id)
        if payload_data:
            html, metadata = payload_data
            return html
        
        # Document not found, generate on-the-fly with default settings
        doc_id = None
    
    # Generate payload
    strategy = os.environ.get("OVERLOAD_STRATEGY", "adversarial")
    size_kb = int(os.environ.get("OVERLOAD_SIZE_KB", "512"))
    num_examples = int(os.environ.get("OVERLOAD_NUM_EXAMPLES", "3"))
    aggression = 2
    
    html, metadata = generate_payload(
        strategy=strategy,
        size_kb=size_kb,
        num_examples=num_examples,
        example_number=example_number,
        aggression_level=aggression
    )
    
    return html


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.post("/api/generate")
def api_generate():
    """Generate a new adversarial document."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Create document metadata
        doc_id = document_store.create_document(data)
        doc_meta = document_store.get_document(doc_id)
        
        # Generate payload
        html, payload_meta = generate_payload(
            strategy=data.get('strategy', 'adversarial'),
            size_kb=data.get('size_kb', 512),
            aggression_level=data.get('aggression', 2),
            doc_category=data.get('doc_category'),
            jailbreak_techniques=doc_meta['jailbreak_techniques']
        )
        
        # Store payload
        document_store.store_payload(doc_id, html, payload_meta)
        
        return jsonify({
            "id": doc_id,
            "strategy": doc_meta['strategy'],
            "size_kb": doc_meta['size_kb'],
            "aggression": doc_meta['aggression'],
            "jailbreak_count": doc_meta['jailbreak_count']
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/documents")
def api_list_documents():
    """List all generated documents."""
    documents = document_store.list_all()
    return jsonify(documents), 200


@app.delete("/api/documents/<doc_id>")
def api_delete_document(doc_id):
    """Delete a document."""
    if document_store.delete(doc_id):
        return jsonify({"status": "deleted"}), 200
    return jsonify({"error": "Document not found"}), 404


@app.get("/api/llm-profiles")
def api_llm_profiles():
    """Get LLM profile configurations."""
    return jsonify(LLM_PROFILES), 200


# ---------------------------------------------------------------------------
# Ollama API Routes
# ---------------------------------------------------------------------------

@app.get("/api/ollama/status")
def api_ollama_status():
    """Check Ollama service status."""
    status = ollama_client.check_status()
    return jsonify(status), 200


@app.get("/api/ollama/models")
def api_ollama_models():
    """List available Ollama models."""
    models = ollama_client.list_models()
    return jsonify(models), 200


@app.post("/api/ollama/chat")
def api_ollama_chat():
    """Send message to Ollama."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        session_id = data.get('session_id')
        model = data.get('model')
        message = data.get('message')
        system = data.get('system')
        
        if not all([session_id, model, message]):
            return jsonify({"error": "Missing required fields"}), 400
        
        response = ollama_client.send_message(
            session_id=session_id,
            model=model,
            message=message,
            system=system
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/ollama/history/<session_id>")
def api_ollama_history(session_id):
    """Get conversation history."""
    history = ollama_client.get_history(session_id)
    if history:
        return jsonify(history), 200
    return jsonify({"error": "Session not found"}), 404


@app.delete("/api/ollama/history/<session_id>")
def api_ollama_clear_history(session_id):
    """Clear conversation history."""
    if ollama_client.clear_history(session_id):
        return jsonify({"status": "cleared"}), 200
    return jsonify({"status": "not_found"}), 404


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    
    print(f"[overload] Starting server on {host}:{port}")
    print(f"[overload] Dashboard: http://localhost:{port}/")
    print(f"[overload] Testing: http://localhost:{port}/test")
    
    app.run(host=host, port=port, debug=False)

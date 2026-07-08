"""
Template Manager for OverLoad Application
Handles loading and rendering of HTML templates.
"""

import os
from typing import Dict, Any, Optional
from flask import render_template


class TemplateManager:
    """Manages HTML templates for the OverLoad application."""
    
    TEMPLATE_DIR = "templates"
    
    TEMPLATES = {
        "dashboard": "unified_dashboard.html",
        "payload": "payload.html",
        "visits": "visits.html",
        "test": "test.html"  # Legacy - kept for backward compatibility
    }
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            template_dir: Optional custom template directory path
        """
        self.template_dir = template_dir or self.TEMPLATE_DIR
        self._validate_templates()
    
    def _validate_templates(self) -> None:
        """Validate that all required templates exist."""
        for name, filename in self.TEMPLATES.items():
            path = os.path.join(self.template_dir, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Template '{name}' not found at {path}")
    
    def render(self, template_name: str, **context: Any) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template (e.g., 'dashboard', 'payload')
            **context: Template context variables
            
        Returns:
            Rendered HTML string
            
        Raises:
            ValueError: If template_name is not recognized
        """
        if template_name not in self.TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")
        
        template_file = self.TEMPLATES[template_name]
        return render_template(template_file, **context)
    
    def render_dashboard(self) -> str:
        """Render the main dashboard page."""
        return self.render("dashboard")
    
    def render_payload(self, doc_title: str, breadcrumb: str, 
                      content_html: str) -> str:
        """
        Render a payload document page.
        
        Args:
            doc_title: Document title
            breadcrumb: Breadcrumb navigation text
            content_html: Main document HTML content
            
        Returns:
            Rendered HTML string
        """
        return self.render("payload",
                          doc_title=doc_title,
                          breadcrumb=breadcrumb,
                          content=content_html)
    
    def render_visits(self, visits_json: str) -> str:
        """
        Render the visits log page.
        
        Args:
            visits_json: JSON string of visit records
            
        Returns:
            Rendered HTML string
        """
        return self.render("visits", visits_json=visits_json)
    
    def render_test(self) -> str:
        """Render the interactive Ollama testing page."""
        return self.render("test")
    
    @classmethod
    def get_template_path(cls, template_name: str) -> str:
        """
        Get the file path for a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Full file path to the template
            
        Raises:
            ValueError: If template_name is not recognized
        """
        if template_name not in cls.TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")
        
        return os.path.join(cls.TEMPLATE_DIR, cls.TEMPLATES[template_name])
    
    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """
        Get a dictionary of all available templates.
        
        Returns:
            Dictionary mapping template names to filenames
        """
        return cls.TEMPLATES.copy()

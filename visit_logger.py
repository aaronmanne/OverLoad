"""
Visit Logging System
Tracks and records document access attempts.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from collections import deque


class VisitLogger:
    """Tracks visits to adversarial documents."""
    
    MAX_VISITS = 500  # Maximum visits to keep in memory
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the visit logger.
        
        Args:
            log_file: Optional path to persistent log file
        """
        self.log_file = log_file or os.environ.get(
            "OVERLOAD_LOG",
            "/app/visits.log"
        )
        self.visits = deque(maxlen=self.MAX_VISITS)
        self._load_existing_logs()
    
    def _load_existing_logs(self) -> None:
        """Load existing visits from log file if it exists."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            visit = json.loads(line.strip())
                            self.visits.append(visit)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Warning: Could not load existing logs: {e}")
    
    def log_visit(self, route: str, ip: str, user_agent: str,
                  referer: Optional[str] = None, 
                  elapsed_ms: Optional[float] = None) -> Dict[str, Any]:
        """
        Log a document visit.
        
        Args:
            route: Route/path that was accessed
            ip: Client IP address
            user_agent: User agent string
            referer: Optional HTTP referer
            elapsed_ms: Optional request processing time in milliseconds
            
        Returns:
            Visit record dictionary
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Determine visit type from user agent
        visit_type = self._classify_visitor(user_agent)
        
        visit = {
            "timestamp": timestamp,
            "route": route,
            "ip": ip,
            "user_agent": user_agent,
            "referer": referer or "-",
            "type": visit_type,
            "elapsed_ms": elapsed_ms
        }
        
        # Add to in-memory deque
        self.visits.append(visit)
        
        # Write to persistent log
        self._write_to_file(visit)
        
        # Print to console
        self._print_visit(visit)
        
        return visit
    
    def _classify_visitor(self, user_agent: str) -> str:
        """
        Classify visitor type based on user agent.
        
        Args:
            user_agent: User agent string
            
        Returns:
            Visitor type: 'bot', 'llm', 'browser', or 'unknown'
        """
        ua_lower = user_agent.lower()
        
        # LLM/AI agents
        llm_indicators = [
            'gpt', 'claude', 'anthropic', 'openai', 'chatgpt',
            'gemini', 'bard', 'llama', 'ai-agent'
        ]
        if any(indicator in ua_lower for indicator in llm_indicators):
            return 'llm'
        
        # Common bots
        bot_indicators = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'http', 'fetch'
        ]
        if any(indicator in ua_lower for indicator in bot_indicators):
            return 'bot'
        
        # Browsers
        browser_indicators = ['mozilla', 'chrome', 'safari', 'firefox', 'edge']
        if any(indicator in ua_lower for indicator in browser_indicators):
            return 'browser'
        
        return 'unknown'
    
    def _write_to_file(self, visit: Dict[str, Any]) -> None:
        """
        Write visit record to persistent log file.
        
        Args:
            visit: Visit record dictionary
        """
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(visit) + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def _print_visit(self, visit: Dict[str, Any]) -> None:
        """
        Print visit to console.
        
        Args:
            visit: Visit record dictionary
        """
        elapsed = f"{visit['elapsed_ms']:.0f}ms" if visit.get('elapsed_ms') else "-"
        print(
            f"[VISIT] {visit['timestamp']}  "
            f"ip={visit['ip']}  "
            f"type={visit['type']}  "
            f"ua='{visit['user_agent'][:50]}'  "
            f"ref={visit['referer']}  "
            f"route={visit['route']}  "
            f"{elapsed}"
        )
    
    def get_all_visits(self) -> List[Dict[str, Any]]:
        """
        Get all visits in memory.
        
        Returns:
            List of visit records
        """
        return list(self.visits)
    
    def get_recent_visits(self, count: int = 50) -> List[Dict[str, Any]]:
        """
        Get most recent visits.
        
        Args:
            count: Number of visits to return
            
        Returns:
            List of recent visit records
        """
        return list(self.visits)[-count:]
    
    def get_visits_by_type(self, visit_type: str) -> List[Dict[str, Any]]:
        """
        Get visits filtered by type.
        
        Args:
            visit_type: Type to filter ('llm', 'bot', 'browser', 'unknown')
            
        Returns:
            Filtered list of visit records
        """
        return [v for v in self.visits if v.get('type') == visit_type]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get visit statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.visits:
            return {
                "total": 0,
                "by_type": {},
                "recent_ips": [],
                "routes": {}
            }
        
        # Count by type
        by_type = {}
        for visit in self.visits:
            vtype = visit.get('type', 'unknown')
            by_type[vtype] = by_type.get(vtype, 0) + 1
        
        # Recent unique IPs
        recent_ips = list(set(
            v.get('ip', 'unknown') 
            for v in list(self.visits)[-50:]
        ))
        
        # Routes accessed
        routes = {}
        for visit in self.visits:
            route = visit.get('route', '/')
            routes[route] = routes.get(route, 0) + 1
        
        return {
            "total": len(self.visits),
            "by_type": by_type,
            "recent_ips": recent_ips,
            "routes": routes
        }
    
    def clear_visits(self) -> int:
        """
        Clear all visits from memory (does not delete log file).
        
        Returns:
            Number of visits cleared
        """
        count = len(self.visits)
        self.visits.clear()
        return count

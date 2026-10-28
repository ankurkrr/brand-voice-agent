"""
Web Research Module for Agent 2
Provides live web signal gathering using Tavily API.

ARD Compliance:
- Extracts signals only (titles, snippets) - NO full page scraping
- No competitor names stored
- No marketing copy generated
- Graceful fallback to LLM-only mode
"""

import os
from typing import Dict, List, Optional
from tavily import TavilyClient


import hashlib
import json

class WebResearchService:
    """
    Tavily-based web research for Agent 2.
    Gathers strategic signals (titles, snippets) without full content scraping.
    """
    
    def _calculate_fingerprint(self, query: str, signals: Dict[str, any]) -> str:
        """
        Generate a deterministic SHA-256 fingerprint of the research source.
        
        Fingerprint = hash(query + sorted_titles + sorted_snippets)
        """
        # Canonicalize data for hashing
        data_to_hash = {
            "query": query,
            "titles": sorted(signals.get("titles", [])),
            "snippets": sorted(signals.get("snippets", []))
        }
        
        serialized = json.dumps(data_to_hash, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    
    def __init__(self):
        """Initialize Tavily client with API key from environment."""
        self.api_key = os.getenv("TAVILY_API_KEY")
        
        if not self.api_key:
            raise RuntimeError(
                "TAVILY_API_KEY not found in environment. "
                "Add TAVILY_API_KEY=tvly-xxx to .env file."
            )
        
        self.client = TavilyClient(api_key=self.api_key)
        print("[WebResearch] Tavily client initialized")
    
    def _build_search_query(self, topic: str, market: str, region: str) -> str:
        """
        Constructs strategic search query for Tavily.
        
        Examples:
            topic="AI in Healthcare", market="Technology", region="US"
            → "AI in Healthcare Technology US trends analysis"
        
        Args:
            topic: Content topic
            market: Target market (e.g., "Technology")
            region: Geographic region (e.g., "US")
        
        Returns:
            Optimized search query string
        """
        parts = [topic]
        
        if market and market not in ["", "General"]:
            parts.append(market)
        
        if region and region not in ["", "Global"]:
            parts.append(region)
        
        parts.append("trends analysis")
        
        query = " ".join(parts)
        print(f"[WebResearch] Search query: {query}")
        return query
    
    def _extract_signals(self, tavily_results: List[dict]) -> Dict[str, any]:
        """
        Deterministically extracts signals from Tavily search results.
        NO LLM - purely rule-based extraction.
        
        Extracts:
            - Page titles (strategic angle signals)
            - Content snippets (truncated to 200 chars)
            - URLs (for auditability only, not stored in DB)
        
        Args:
            tavily_results: Raw Tavily API response results
        
        Returns:
            {
                "titles": [...],
                "snippets": [...],
                "urls": [...],
                "signal_count": int
            }
        """
        titles = []
        snippets = []
        urls = []
        
        for result in tavily_results:
            # Extract title (strategic signal)
            title = result.get('title', '').strip()
            if title:
                titles.append(title)
            
            # Extract snippet (truncated for signal extraction only)
            content = result.get('content', '').strip()
            if content:
                # Truncate to 200 chars to prevent prose storage
                snippet = content[:200]
                if len(content) > 200:
                    snippet += "..."
                snippets.append(snippet)
            
            # Extract URL (audit trail only)
            url = result.get('url', '')
            if url:
                urls.append(url)
        
        # Limit to top 10 results
        return {
            "titles": titles[:10],
            "snippets": snippets[:10],
            "urls": urls[:10],
            "results": tavily_results[:10],  # NEW: Full results for research_scope
            "signal_count": len(tavily_results)
        }
    
    async def gather_web_signals(
        self,
        topic: str,
        market: str = "",
        region: str = "",
        pipeline_id: str = "unknown_pipeline"
    ) -> Dict[str, any]:
        """
        Searches the web using Tavily and extracts strategic signals.
        
        ARD-Compliant:
            ✅ Signals only (titles, snippets)
            ❌ No full page scraping
            ❌ No competitor names stored
            ❌ No marketing copy
        
        Args:
            topic: Content topic to research
            market: Target market/industry (optional)
            region: Geographic region (optional)
        
        Returns:
            {
                "titles": ["...", "..."],     # Strategic angles
                "snippets": ["...", "..."],   # Context snippets (200 chars max)
                "urls": ["...", "..."],       # Audit trail
                "signal_count": 10,
                "query": "..."                # Search query used
            }
        
        Raises:
            Exception: If Tavily API call fails (caller should handle fallback)
        """
        query = self._build_search_query(topic, market, region)
        
        try:
            print(f"[WebResearch] Calling Tavily API...")
            
            import time
            import uuid
            from core.execution.token_tracker import TokenTracker
            tracker = TokenTracker()
            request_id = str(uuid.uuid4())
            start_time = time.perf_counter()

            # Call Tavily API
            response = self.client.search(
                query=query,
                max_results=10,
                search_depth="basic",  # Fast, surface-level scan
                include_domains=[],    # No restrictions
                exclude_domains=[]     # No exclusions
            )
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            await tracker.track_tavily_usage(
                request_id=request_id,
                pipeline_id=pipeline_id,
                agent_name="agent2_ideation",
                latency_ms=latency_ms,
                metadata={"query": query, "tavily_results": len(response.get('results', []))}
            )

            # Extract results
            results = response.get('results', [])
            
            if not results:
                print(f"[WebResearch] No results found for query: {query}")
                return {
                    "titles": [],
                    "snippets": [],
                    "urls": [],
                    "signal_count": 0,
                    "query": query
                }
            
            # Extract signals (deterministic)
            signals = self._extract_signals(results)
            signals["query"] = query
            
            # CDM-3: Deterministic Source Fingerprinting
            fingerprint = self._calculate_fingerprint(query, signals)
            signals["fingerprint"] = fingerprint
            
            print(f"[WebResearch] Extracted {signals['signal_count']} signals. Fingerprint: {fingerprint}")
            return signals
            
        except Exception as e:
            print(f"[WebResearch] Tavily API error: {str(e)}")
            raise  # Caller will handle fallback


# Singleton instance
_web_research_service: Optional[WebResearchService] = None


async def gather_web_signals(
    topic: str,
    market: str = "",
    region: str = "",
    pipeline_id: str = "unknown_pipeline"
) -> Dict[str, any]:
    """
    Convenience function to gather web signals.
    Uses singleton WebResearchService instance.
    
    Graceful fallback: If Tavily fails, returns empty signals
    (caller can proceed with LLM-only mode).
    """
    global _web_research_service
    
    try:
        # Initialize service on first call
        if _web_research_service is None:
            _web_research_service = WebResearchService()
        
        # Gather signals
        return await _web_research_service.gather_web_signals(topic, market, region, pipeline_id=pipeline_id)
    
    except RuntimeError as e:
        # API key missing - fallback to empty signals
        print(f"[WebResearch] Configuration error: {e}")
        print("[WebResearch] Falling back to LLM-only mode")
        return {
            "titles": [],
            "snippets": [],
            "urls": [],
            "signal_count": 0,
            "query": topic
        }
    
    except Exception as e:
        # API call failed - fallback to empty signals
        print(f"[WebResearch] Error: {e}")
        print("[WebResearch] Falling back to LLM-only mode")
        return {
            "titles": [],
            "snippets": [],
            "urls": [],
            "results": [],  # NEW
            "signal_count": 0,
            "query": topic
        }

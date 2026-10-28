"""
Signal Collector Layer (Agent 2)

Responsible for pure data extraction from the SERP.
No LLM logic. Pure data.
"""

import os
import re
from typing import Dict, List, Optional
from pydantic import BaseModel
from tavily import TavilyClient
import hashlib
import json

class CompetitiveSignals(BaseModel):
    serp_headings: List[str]
    competitor_angles: List[str]
    extracted_statistics: List[str]
    related_queries: List[str]
    fingerprint: str = ""

class SignalCollector:
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            print("[SignalCollector] TAVILY_API_KEY missing. Fallback mode enabled.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=self.api_key)

    def _extract_stats(self, text: str) -> List[str]:
        """Extract sentences that contain numbers/statistics."""
        stats = []
        # Basic split by period
        sentences = text.replace('?', '.').replace('!', '.').split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            # If it contains a number and is reasonably long
            if re.search(r'\d', sentence) and len(sentence.split()) > 3:
                stats.append(sentence)
        return stats

    def _calculate_fingerprint(self, query: str, results: List[dict]) -> str:
        data_to_hash = {"query": query, "urls": [r.get("url", "") for r in results]}
        serialized = json.dumps(data_to_hash, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    async def collect_signals(self, topic: str, market: str = "", region: str = "") -> CompetitiveSignals:
        """Call Tavily and parse results into competitive signals."""
        query = f"{topic} {market} {region}".strip()
        
        if not self.client:
            return CompetitiveSignals(
                serp_headings=[], competitor_angles=[], extracted_statistics=[], related_queries=[]
            )

        try:
            # We use advanced search to get more content
            response = self.client.search(
                query=query,
                max_results=5,
                search_depth="advanced"
            )
            
            results = response.get('results', [])
            
            headings = []
            angles = []
            stats = []
            
            for result in results:
                title = result.get('title', '')
                content = result.get('content', '')
                
                if title:
                    headings.append(title)
                    angles.append(title) # Titles often contain the core angle
                    
                if content:
                    stats.extend(self._extract_stats(content))
                    
            return CompetitiveSignals(
                serp_headings=headings,
                competitor_angles=angles,
                extracted_statistics=stats[:10], # Keep top 10 stats to avoid context bloat
                related_queries=[], # Tavily doesn't return related queries directly in basic search
                fingerprint=self._calculate_fingerprint(query, results)
            )

        except Exception as e:
            print(f"[SignalCollector] Tavily failed: {e}")
            return CompetitiveSignals(
                serp_headings=[], competitor_angles=[], extracted_statistics=[], related_queries=[]
            )

# Singleton
_collector = None
async def collect_signals(topic: str, market: str = "", region: str = "") -> CompetitiveSignals:
    global _collector
    if _collector is None:
        _collector = SignalCollector()
    return await _collector.collect_signals(topic, market, region)

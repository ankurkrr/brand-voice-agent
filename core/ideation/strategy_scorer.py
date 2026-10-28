"""
Strategy Scorer Layer (Agent 2)

Evaluates the generated StrategicBrief.
Combines deterministic schema checks with LLM qualitative checks.
Output: Composite Score (0.0 - 10.0). Retries triggered if < 7.0.
"""

from pydantic import BaseModel
from typing import Dict

# ---------------------------------------------------------
# Deterministic Scorer
# ---------------------------------------------------------
class DeterministicScorer:
    """Hard-coded checks for depth and gap alignment."""
    
    @staticmethod
    def score_brief(brief: dict, gap_analysis: dict, raw_signals: list = None) -> tuple[float, dict]:
        breakdown = {
            "gap_alignment": 10.0,
            "persona_depth": 10.0,
            "differentiation_alignment": 10.0,
            "structural_originality": 10.0,
            "buyer_stage_alignment": 10.0
        }
        
        content = brief.get("content_brief", brief)
        
        # 0. Sanity Validation (Must have Gap Data)
        if not gap_analysis.get("saturated_themes"):
            print("[-5.0 SCORER PENALTY] Analyzer failed to detect saturated themes. FAILING.")
            breakdown["gap_alignment"] -= 5.0
            
        # 1. Persona Depth (Deep Schema flattening)
        pain_point = content.get("persona_primary_pain_point", "")
        if not pain_point or len(pain_point) <= 15:
            breakdown["persona_depth"] = 2.0
        elif len(pain_point) <= 30:
            breakdown["persona_depth"] = 5.0
        else:
            breakdown["persona_depth"] = 10.0
            
        # 1.5 Differentiation Strategy explicitly captured
        diff_strategy = content.get("differentiation_strategy", "")
        if not diff_strategy or len(diff_strategy) <= 15:
            breakdown["differentiation_alignment"] = 2.0
        elif len(diff_strategy) <= 50:
            breakdown["differentiation_alignment"] = 5.0
        else:
            breakdown["differentiation_alignment"] = 10.0
            
        # 2. Structural Outline & Saturation Penalty
        outline = content.get("h2_outline", [])
        if len(outline) < 3:
            breakdown["structural_originality"] -= 5.0
        elif len(outline) < 5:
            breakdown["structural_originality"] -= 2.0
            
        # PENALTY: Are we just repeating saturated themes?
        saturated = [s.lower() for s in gap_analysis.get("saturated_themes", [])]
        overlap_count = 0
        for h2 in outline:
            if any(s in h2.lower() or h2.lower() in s for s in saturated):
                overlap_count += 1
                
        if overlap_count > 2:
            breakdown["structural_originality"] -= 3.0 # Heavy penalty for generic template
            print(f"[-3.0 SCORER PENALTY] Too much overlap with Saturated Themes: {overlap_count} headings.")
            
        # PENALTY: Did we exploit ANY gaps?
        underexplored = [u.lower() for u in gap_analysis.get("underexplored_angles", [])]
        exploited_angles = set()
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            if underexplored and outline:
                vectorizer = TfidfVectorizer(stop_words='english')
                corpus = underexplored + outline
                vectorizer.fit(corpus)
                
                h2_vecs = vectorizer.transform(outline)
                for u in underexplored:
                    u_vec = vectorizer.transform([u])
                    similarities = cosine_similarity(h2_vecs, u_vec).flatten()
                    if len(similarities) > 0 and similarities.max() > 0.55:
                        exploited_angles.add(u)
        except ImportError:
            # Fallback to brittle string matching if text evaluation engine isn't installed
            print("[SCORER WARNING] scikit-learn not installed. Falling back to brittle Gap Alignment matching.")
            for h2 in outline:
                for u in underexplored:
                    if u in h2.lower() or h2.lower() in u:
                        exploited_angles.add(u)
                
        if len(exploited_angles) < 2 and len(underexplored) >= 2:
            breakdown["gap_alignment"] -= 4.0 # Severe penalty for failing to differentiate deeply
            print(f"[-4.0 SCORER PENALTY] Only {len(exploited_angles)} underexplored angles utilized in outline (Minimum 2 required for ARD Level 8).")
        elif not exploited_angles and underexplored:
            breakdown["gap_alignment"] -= 6.0 
            print(f"[-6.0 SCORER PENALTY] Zero underexplored angles utilized.")
            
        # ======= NEW: STRATEGIC COHERENCE ENGINE (ARD Level 6) =======
        
        outline_str = " ".join(outline).lower()
        
        # Coherence 1: Outline must reflect pain points
        pain_words = [w.lower() for w in pain_point.split() if len(w) > 4]
        pain_matches = sum(1 for h2 in outline for w in pain_words if w in h2.lower())
        if pain_matches < 2 and pain_words:
            breakdown["persona_depth"] -= 3.0
            print(f"[-3.0 SCORER PENALTY] Persona pain points do not manifest deeply in H2 outline. ({pain_matches}/2 required)")
            
        # Coherence 2: Outline must reflect differentiation strategy
        diff_words = [w.lower() for w in diff_strategy.split() if len(w) > 4]
        diff_matches = sum(1 for h2 in outline for w in diff_words if w in h2.lower())
        if diff_matches < 3 and diff_words:
            breakdown["differentiation_alignment"] -= 3.0
            print(f"[-3.0 SCORER PENALTY] Differentiation strategy not reflected strongly in H2 outline. ({diff_matches}/3 required)")

        # Coherence 3: Search Intent to Structure Mapping
        intent = content.get("search_intent", "")
        if intent == "Investigational" and not any(w in outline_str for w in ["vs", "compare", "evaluate", "best", "versus", "top", "review", "guide", "alternative"]):
            breakdown["structural_originality"] -= 3.0
            print("[-3.0 SCORER PENALTY] Investigational intent lacks comparison/evaluation sections.")
        elif intent == "Transactional" and not any(w in outline_str for w in ["roi", "cost", "implement", "price", "vendor", "deploy", "decision", "buy", "service"]):
            breakdown["structural_originality"] -= 3.0
            print("[-3.0 SCORER PENALTY] Transactional intent lacks implementation/ROI sections.")
            
        # Coherence 4: Buyer Stage alignment
        stage = content.get("buyer_stage", "")
        if stage == "Middle" and not any(w in outline_str for w in ["risk", "implement", "roi", "challenge", "barrier", "consideration"]):
            breakdown["buyer_stage_alignment"] -= 3.0
            print("[-3.0 SCORER PENALTY] Middle-funnel lacks risk/implementation sections.")
        elif stage == "Bottom" and not any(w in outline_str for w in ["compare", "vendor", "roadmap", "buy", "decision", "checklist", "case"]):
            breakdown["buyer_stage_alignment"] -= 3.0
            print("[-3.0 SCORER PENALTY] Bottom-funnel lacks comparison/decision sections.")

        # Coherence 5: True Semantic Density Model (ARD Phase 10)
        # Uses TF-IDF embedding similarity to validate archetypes (synonym-aware, non-brittle)
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            ARCHETYPES = {
                "regulatory": "compliance audit oversight mandate legal standard mitigation accountability certification gdpr iso enforcement penalty",
                "economic": "roi payback sensitivity tradeoff allocation amortization opex capex baseline forecast margin threshold modeling",
                "technical": "latency throughput payload architecture telemetry concurrency pipeline caching redundancy failover microservices api compute",
                "operational": "bottleneck velocity metric tracking delta scorecard SLA utilization downtime onboarding sprint tracking optimization",
                "strategic": "moat cannibalization disruption paradigm synergy monopoly tailwinds headwinds positioning whitespace thesis contrarian"
            }
            
            claimed_text = diff_strategy.lower() + " " + " ".join(u.lower() for u in underexplored)
            claimed_archetypes = [arch for arch in ARCHETYPES.keys() if arch in claimed_text]
            
            if claimed_archetypes and outline:
                vectorizer = TfidfVectorizer(stop_words='english')
                # Fit corpus: all archetypes + all H2s
                corpus = list(ARCHETYPES.values()) + outline
                vectorizer.fit(corpus)
                
                h2_vecs = vectorizer.transform(outline)
                archetypes_covered_count = 0
                
                for arch in claimed_archetypes:
                    cluster_vec = vectorizer.transform([ARCHETYPES[arch]])
                    similarities = cosine_similarity(h2_vecs, cluster_vec).flatten()
                    density_score = similarities.max() if len(similarities) > 0 else 0.0
                    
                    if density_score < 0.15: # Threshold for TF-IDF overlap
                        # Scales penalty from 0 to max 4.0 depending on how low the score is
                        density_penalty = min(4.0, (0.15 - density_score) * (4.0 / 0.15)) 
                        breakdown["structural_originality"] -= density_penalty
                        print(f"[-{density_penalty:.1f} SCORER PENALTY] Claimed '{arch}' archetype, but H2 semantic density was too low ({density_score:.2f} vs 0.15 threshold).")
                    else:
                        archetypes_covered_count += 1
                        
                # Archetype Diversity Bonus
                if archetypes_covered_count >= 3:
                    breakdown["structural_originality"] += 2.0
                    print(f"[+2.0 SCORER BONUS] Exceptional Structural Diversity. Covered {archetypes_covered_count} strategic archetypes with high semantic density.")
        except ImportError:
            print("[SCORER WARNING] scikit-learn not installed. Skipping Semantic Density Engine.")

        # Coherence 6: Strict Sub-Layer Depth Validator (ARD Phase 12 - Breakout)
        # If the LLM mentions a high-level concept, it MUST provide execution-level depth structure.
        
        outline_lower = " ".join(outline).lower()
        diff_strat_lower = diff_strategy.lower()
        
        # 6a. Economic / ROI Depth
        capex_terms = ["investment", "capex", "budget", "finance", "financial", "cost", "revenue", "roi", "tco"]
        claimed_capex = any(t in diff_strat_lower or t in pain_point.lower() for t in capex_terms)
        
        if claimed_capex:
            economic_depth_terms = ["payback", "horizon", "risk-adjusted", "tradeoff", "capital allocation", "cost of inaction", "sensitivity analysis", "cost breakdown", "modeling"]
            if not any(w in outline_lower for w in economic_depth_terms):
                breakdown["structural_originality"] -= 4.0
                print(f"[-4.0 SCORER PENALTY] Shallow Economic Framing: Claimed financial/ROI angle but lacked deep execution structure (e.g. payback horizon, tradeoffs, sensitivity analysis).")

        # 6b. Governance / Risk Depth
        gov_terms = ["governance", "risk", "ethics", "regulatory", "compliance", "privacy", "security"]
        claimed_gov = any(t in diff_strat_lower or t in pain_point.lower() for t in gov_terms)
        
        if claimed_gov:
            gov_depth_terms = ["audit", "oversight", "accountability", "framework", "mandate", "legal", "standardized", "mitigation"]
            if not any(w in outline_lower for w in gov_depth_terms):
                breakdown["structural_originality"] -= 4.0
                print(f"[-4.0 SCORER PENALTY] Shallow Governance Framing: Claimed risk/ethics angle but lacked structural oversight depth (e.g. audit, accountability, mitigation matrices).")
                
        # 6c. Performance / KPI Depth
        perf_terms = ["performance", "optimize", "efficiency", "growth", "scale", "throughput", "velocity", "kpi"]
        claimed_perf = any(t in diff_strat_lower or t in pain_point.lower() for t in perf_terms)
        
        if claimed_perf:
            perf_depth_terms = ["baseline", "delta", "measurable", "threshold", "scorecard", "optimization loop", "benchmarks", "tracking"]
            if not any(w in outline_lower for w in perf_depth_terms):
                breakdown["structural_originality"] -= 3.0
                print(f"[-3.0 SCORER PENALTY] Shallow Performance Framing: Claimed scale/efficiency angle but lacked measurement depth (e.g. baselines, sub-deltas, thresholds, tracking).")

        # Coherence 7: Semantic Uniqueness Score vs Raw SERP (ARD Phase 12)
        if raw_signals and outline:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                
                vectorizer = TfidfVectorizer(stop_words='english')
                corpus = raw_signals + outline
                vectorizer.fit(corpus)
                
                h2_vecs = vectorizer.transform(outline)
                serp_vecs = vectorizer.transform(raw_signals)
                
                similarities = cosine_similarity(h2_vecs, serp_vecs)
                max_similarity = similarities.max() if similarities.size > 0 else 0.0
                
                if max_similarity > 0.65:
                    # Scales penalty from 0 to 5.0 based on how severe the plagiarism/template matching is
                    uniqueness_penalty = min(5.0, (max_similarity - 0.65) * 10)
                    breakdown["structural_originality"] -= uniqueness_penalty
                    print(f"[-{uniqueness_penalty:.1f} SCORER PENALTY] Semantic Uniqueness Failure: H2 outline is too similar to raw SERP headings (Similarity: {max_similarity:.2f} > 0.65).")
                elif max_similarity < 0.35:
                    breakdown["structural_originality"] += 2.0
                    print(f"[+2.0 SCORER BONUS] Strong Semantic Originality against raw SERP (Max Similarity: {max_similarity:.2f} < 0.35).")
                else:
                    print(f"[0.0 SCORER NEUTRAL] Semantic Originality within acceptable zone (Max Similarity: {max_similarity:.2f}).")
            except ImportError:
                print("[SCORER WARNING] scikit-learn not installed. Skipping Semantic Uniqueness Engine.")

        # Coherence 8: ARD Level 8 Defensibility Mandate (Phase 12 Extension)
        # The outline MUST include at least one of: KPI/Measurement, Phased Roadmap, or Comparative Framework
        defensibility_matrix = {
            "kpi_measurement": ["kpi", "metric", "measure", "threshold", "playbook", "scorecard", "success criteria", "dashboard"],
            "phased_roadmap": ["phase", "roadmap", "timeline", "pilot", "scale", "rollout", "milestone", "stage"],
            "comparative_framework": ["benchmark", "matrix", "vs", "evaluation model", "comparison", "build vs buy", "evaluation framework"]
        }
        
        has_defensibility = False
        for category, terms in defensibility_matrix.items():
            # Check if any term in the category matches any H2 outline string
            if any(w in h2.lower() for h2 in outline for w in terms):
                has_defensibility = True
                break
                
        if not has_defensibility:
            breakdown["structural_originality"] -= 3.0
            print("[-3.0 SCORER PENALTY] ARD Level 8 Failure: Outline lacks a KPI framework, Phased Roadmap, or Comparative Matrix.")

        # Normalization Layer: Prevent over-penalization cascade
        total_raw_penalty = 50.0 - sum(breakdown.values())
        MAX_PENALTY = 25.0  # Caps the maximum deterministic penalty
        final_penalty = min(MAX_PENALTY, total_raw_penalty)
        
        # Calculate final deterministic score after normalized penalty
        score = (50.0 - final_penalty) / len(breakdown)
        
        # Ensure bounds 0-10 for UI mapping
        for k in breakdown:
            breakdown[k] = max(min(breakdown[k], 10.0), 0.0)

        return score, breakdown

# ---------------------------------------------------------
# LLM Scorer
# ---------------------------------------------------------
class LLMScorer:
    """Qualitative check for strategic reasoning."""
    
    @staticmethod
    async def score_brief(llm, brief: dict, gap_analysis: dict, pipeline_id: str = "unknown_pipeline") -> float:
        import json
        brief_str = json.dumps(brief)
        gap_str = json.dumps(gap_analysis)
        
        prompt = f"""
        Rate the Strategic Quality of this Content Brief from 0 to 10.
        
        CRITICAL RULES:
        1. If the brief's H2 Outline does NOT explore the 'underexplored_angles' listed in the Gap Analysis, the MAXIMUM score is 5.0.
        2. If the Persona's 'primary_pain_point' is overly broad or superficial, the MAXIMUM score is 5.0.
        3. If the 'differentiation_strategy' is vague and fails to explicitly avoid 'saturated_themes', the MAXIMUM score is 5.0.
        
        Gap Analysis Data (The Ground Truth):
        {gap_str}
        
        Generated Brief to Evaluate:
        {brief_str[:1500]}...
        
        Criteria for 8.0+:
        - Intent clearly aligns with the specified buyer_stage.
        - differentiation_strategy is surgically precise.
        - The outline explicitly tackles an Underexplored Angle from the Gap Data in a way that aligns with the Persona's pain point.
        - Keyword clustering makes sense for the niche.
        
        Respond with ONLY a number between 0.0 and 10.0.
        """
        
        try:
            import time
            import uuid
            from core.execution.token_tracker import TokenTracker
            tracker = TokenTracker()
            request_id = str(uuid.uuid4())
            start_time = time.perf_counter()

            response = await llm.ainvoke([{"role": "user", "content": prompt}])
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            await tracker.track_llm_usage(
                request_id=request_id,
                pipeline_id=pipeline_id,
                agent_name="agent2_ideation",
                provider="gemini",
                model=getattr(llm, "model", "gemini-2.5-flash"),
                response=response,
                latency_ms=latency_ms
            )

            content = response.content.strip()
            
            import re
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", content)
            if numbers:
                score = float(numbers[0])
                if 0 <= score <= 10:
                    return score
            return 5.0
        except Exception as e:
            print(f"[LLMScorer] Failed to score: {e}")
            return 5.0

# ---------------------------------------------------------
# Composite Scorer
# ---------------------------------------------------------
class StrategyScorer:
    """Calculates the final composite score based on the ARD formula."""
    
    @staticmethod
    async def evaluate(llm, brief: dict, gap_analysis: dict, vulnerability_score: float = 0.0, raw_signals: list = None, pipeline_id: str = "unknown_pipeline") -> tuple[float, dict]:
        
        deterministic_score, breakdown = DeterministicScorer.score_brief(brief, gap_analysis, raw_signals)
        llm_score = await LLMScorer.score_brief(llm, brief, gap_analysis, pipeline_id)
        
        breakdown["llm_strategic_reasoning"] = llm_score
        breakdown["competitor_vulnerability"] = vulnerability_score
        
        # ARD Level 10 Explicit Weight Mapping
        # Making the final calculation fully transparent and mathematically coupled to the breakdown metrics
        WEIGHTS = {
            "gap_alignment": 0.20,
            "persona_depth": 0.15,
            "differentiation_alignment": 0.15,
            "structural_originality": 0.10,
            "buyer_stage_alignment": 0.10,
            "llm_strategic_reasoning": 0.20,
            "competitor_vulnerability": 0.10
        }
        
        # Invert vulnerability (Lower vulnerability = Higher score)
        # Vulnerability is 0 to 5. We map it to a 0 to 10 scale where 0 vuln = 10 score.
        vuln_score_mapped = 10.0 - (vulnerability_score * 2.0)
        
        composite = (
            (breakdown["gap_alignment"] * WEIGHTS["gap_alignment"]) +
            (breakdown["persona_depth"] * WEIGHTS["persona_depth"]) +
            (breakdown["differentiation_alignment"] * WEIGHTS["differentiation_alignment"]) +
            (breakdown["structural_originality"] * WEIGHTS["structural_originality"]) +
            (breakdown["buyer_stage_alignment"] * WEIGHTS["buyer_stage_alignment"]) +
            (llm_score * WEIGHTS["llm_strategic_reasoning"]) +
            (vuln_score_mapped * WEIGHTS["competitor_vulnerability"])
        )
        
        composite = max(min(composite, 10.0), 0.0)
        
        print(f"[StrategyScorer] Final Weighted Composite=({composite:.1f}) | Vuln={vulnerability_score:.1f}")
        return round(composite, 2), breakdown
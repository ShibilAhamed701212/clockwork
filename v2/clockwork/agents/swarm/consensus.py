from typing import Dict, List, Optional

class ConsensusEngine:
    def vote(self, results: List[Dict]) -> Optional[Dict]:
        if not results:
            return None
        success_results = [r for r in results if r.get("success")]
        if not success_results:
            return results[0]
        score_map: Dict[str, int] = {}
        for r in success_results:
            key = str(r.get("output", ""))[:100]
            score_map[key] = score_map.get(key, 0) + 1
        best_key = max(score_map, key=score_map.get)
        for r in success_results:
            if str(r.get("output", ""))[:100] == best_key:
                return r
        return success_results[0]

    def majority(self, decisions: List[str]) -> str:
        if not decisions:
            return "REJECTED"
        counts: Dict[str, int] = {}
        for d in decisions:
            counts[d] = counts.get(d, 0) + 1
        return max(counts, key=counts.get)

    def confidence(self, results: List[Dict]) -> float:
        if not results:
            return 0.0
        success = sum(1 for r in results if r.get("success"))
        return round(success / len(results), 3)

    def merge_explanations(self, results: List[Dict]) -> Dict:
        changes  = list({r.get("explanation", {}).get("change", "") for r in results if r.get("explanation")})
        impacts  = list({r.get("explanation", {}).get("impact", "") for r in results if r.get("explanation")})
        return {
            "changes":    [c for c in changes if c],
            "impacts":    [i for i in impacts if i],
            "confidence": self.confidence(results),
            "agents":     len(results),
        }
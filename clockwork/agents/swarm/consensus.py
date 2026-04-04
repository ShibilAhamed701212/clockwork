from __future__ import annotations


class ConsensusEngine:
    def vote(self, results: list[dict]) -> dict | None:
        if not results:
            return None
        success_results = [result for result in results if result.get("success")]
        if not success_results:
            return results[0]
        score_map: dict[str, int] = {}
        for result in success_results:
            key = str(result.get("output", ""))[:100]
            score_map[key] = score_map.get(key, 0) + 1
        best_key = max(score_map, key=score_map.get)
        for result in success_results:
            if str(result.get("output", ""))[:100] == best_key:
                return result
        return success_results[0]

    def majority(self, decisions: list[str]) -> str:
        if not decisions:
            return "REJECTED"
        counts: dict[str, int] = {}
        for decision in decisions:
            counts[decision] = counts.get(decision, 0) + 1
        return max(counts, key=counts.get)

    def confidence(self, results: list[dict]) -> float:
        if not results:
            return 0.0
        success = sum(1 for result in results if result.get("success"))
        return round(success / len(results), 3)

    def merge_explanations(self, results: list[dict]) -> dict:
        changes = list({result.get("explanation", {}).get("change", "") for result in results if result.get("explanation")})
        impacts = list({result.get("explanation", {}).get("impact", "") for result in results if result.get("explanation")})
        return {
            "changes": [value for value in changes if value],
            "impacts": [value for value in impacts if value],
            "confidence": self.confidence(results),
            "agents": len(results),
        }


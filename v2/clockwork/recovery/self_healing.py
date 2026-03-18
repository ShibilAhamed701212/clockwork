import json
import time
from pathlib import Path
from typing import Dict, List

FAILURE_LOG = Path("recovery/logs/failure_log.json")

class SelfHealing:
    def __init__(self, context=None, state=None):
        self.context = context
        self.state   = state
        FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not FAILURE_LOG.exists():
            FAILURE_LOG.write_text("[]")

    def heal(self, failure: Dict) -> bool:
        ftype    = failure.get("type","")
        details  = failure.get("details","")
        print("[SelfHealing] Attempting to heal: " + ftype)
        self._log_failure(failure)

        healers = {
            "missing_file":         self._heal_missing_file,
            "invalid_context":      self._heal_invalid_context,
            "graph_corruption":     self._heal_graph,
            "index_corruption":     self._heal_index,
            "state_inconsistency":  self._heal_state,
        }
        healer = healers.get(ftype, self._heal_generic)
        try:
            result = healer(failure)
            if result:
                print("[SelfHealing] Healed: " + ftype)
            else:
                print("[SelfHealing] Could not heal: " + ftype)
            return result
        except Exception as e:
            print("[SelfHealing] Heal error: " + str(e))
            return False

    def _heal_missing_file(self, failure: Dict) -> bool:
        path = failure.get("path","")
        if not path:
            return False
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        defaults = {".json":"{}",".yaml":"",".txt":"",".py":"",".md":""}
        default  = defaults.get(p.suffix, "")
        p.write_text(default)
        return True

    def _heal_invalid_context(self, failure: Dict) -> bool:
        ctx_path = Path(".clockwork/context.yaml")
        if not ctx_path.exists():
            ctx_path.write_text("")
            return True
        from context.context_store import ContextStore
        store = ContextStore()
        store.load()
        return True

    def _heal_graph(self, failure: Dict) -> bool:
        db = Path(".clockwork/knowledge_graph.db")
        if db.exists():
            db.unlink()
            print("[SelfHealing] Graph DB cleared — will rebuild on next scan.")
        return True

    def _heal_index(self, failure: Dict) -> bool:
        idx = Path(".clockwork/index.db")
        if idx.exists():
            idx.unlink()
            print("[SelfHealing] Index DB cleared — will rebuild.")
        return True

    def _heal_state(self, failure: Dict) -> bool:
        if self.state:
            self.state.reset()
            print("[SelfHealing] State reset.")
        return True

    def _heal_generic(self, failure: Dict) -> bool:
        print("[SelfHealing] No specific healer for: " + failure.get("type","unknown"))
        return False

    def _log_failure(self, failure: Dict):
        entry = {**failure, "timestamp": time.time(), "healed": False}
        log   = json.loads(FAILURE_LOG.read_text())
        log.append(entry)
        FAILURE_LOG.write_text(json.dumps(log[-200:], indent=2))

    def get_failure_log(self) -> List[Dict]:
        return json.loads(FAILURE_LOG.read_text())

    def failure_rate(self) -> float:
        log = self.get_failure_log()
        if not log:
            return 0.0
        recent  = [e for e in log if time.time() - e.get("timestamp",0) < 3600]
        healed  = sum(1 for e in recent if e.get("healed"))
        return round(len(recent) / max(1, len(log)), 3)
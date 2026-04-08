from dataclasses import dataclass, fields, asdict


@dataclass
class APIDetailsRecord:
    user_id: Optional[str]
    job_id: Optional[str]
    team_id: Optional[str]

    # ---- Dict-compatible access for downstream consumers ----

    def get(self, key: str, default=None):
        """Dict-like .get() so ep.get('node_id') works on dataclass instances."""
        return getattr(self, key, default)

    def __getitem__(self, key: str):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def __setitem__(self, key: str, value):
        """Allow ep['dependencies'] = [...] style writes."""
        object.__setattr__(self, key, value)

    def to_dict(self) -> dict:
        return asdict(self)

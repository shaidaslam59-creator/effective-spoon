"""Explicit registry; ambiguous dispatch is rejected rather than guessed."""
from core.agent import Agent

class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        if agent.name in self._agents:
            raise ValueError("agent_already_registered")
        if not agent.capabilities:
            raise ValueError("agent_has_no_capabilities")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise LookupError("agent_not_found") from exc

    def select(self, task_type: str, requested_agent: str | None = None) -> Agent:
        if requested_agent:
            agent = self.get(requested_agent)
            if task_type not in agent.capabilities:
                raise LookupError("agent_capability_missing")
            return agent
        matches = [a for a in self._agents.values() if task_type in a.capabilities]
        if len(matches) != 1:
            raise LookupError("agent_selection_ambiguous_or_missing")
        return matches[0]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))

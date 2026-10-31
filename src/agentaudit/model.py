"""Normalized view of an AI agent, independent of how it was built."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict | None = None
    source: str = ""  # file path (or "live:tools/list") the definition came from


@dataclass
class Artifact:
    """One piece of text the agent reads or runs, with where it came from."""

    kind: str  # tool_description | instructions | script | readme | config
    path: str
    text: str


@dataclass
class Agent:
    name: str
    origin: str  # repo path, URL or manifest file
    tools: list[Tool] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    declared: dict = field(default_factory=dict)  # owner, purpose, etc. when a manifest states them

    def by_kind(self, kind: str) -> list[Artifact]:
        return [a for a in self.artifacts if a.kind == kind]

    def to_dict(self) -> dict:
        return asdict(self)

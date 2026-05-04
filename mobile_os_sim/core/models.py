from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProcessState(str, Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    TERMINATED = "TERMINATED"


@dataclass
class Process:
    pid: int
    name: str
    memory_mb: int
    priority: int
    state: ProcessState = ProcessState.NEW
    cpu_ticks: int = 0
    blocked_ticks_remaining: int = 0
    block_reason: str | None = None
    waiting_resource: str | None = None
    held_resources: set[str] = field(default_factory=set)
    quantum_used: int = 0
    created_tick: int = 0
    inherited_priority: int | None = None
    io_operation: str | None = None

    @property
    def effective_priority(self) -> int:
        return self.inherited_priority or self.priority

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "memory_mb": self.memory_mb,
            "priority": self.priority,
            "effective_priority": self.effective_priority,
            "state": self.state.value,
            "cpu_ticks": self.cpu_ticks,
            "blocked_ticks_remaining": self.blocked_ticks_remaining,
            "block_reason": self.block_reason,
            "waiting_resource": self.waiting_resource,
            "held_resources": sorted(self.held_resources),
            "quantum_used": self.quantum_used,
            "created_tick": self.created_tick,
            "io_operation": self.io_operation,
        }


@dataclass
class ResourceLock:
    name: str
    owner_pid: int | None = None
    wait_queue: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "owner_pid": self.owner_pid,
            "wait_queue": list(self.wait_queue),
        }

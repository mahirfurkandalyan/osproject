from __future__ import annotations

from collections import deque

from mobile_os_sim.core.models import Process, ProcessState


class BaseScheduler:
    name = "BASE"

    def pick(self, processes: list[Process], current_pid: int | None, quantum: int) -> int | None:
        raise NotImplementedError


class FIFOScheduler(BaseScheduler):
    name = "FIFO"

    def pick(self, processes: list[Process], current_pid: int | None, quantum: int) -> int | None:
        runnable = [p for p in processes if p.state in {ProcessState.READY, ProcessState.RUNNING}]
        if not runnable:
            return None
        running = next((p for p in runnable if p.pid == current_pid and p.state == ProcessState.RUNNING), None)
        if running:
            return running.pid
        runnable.sort(key=lambda p: (p.created_tick, p.pid))
        return runnable[0].pid


class RoundRobinScheduler(BaseScheduler):
    name = "ROUND_ROBIN"

    def __init__(self) -> None:
        self.rotation = deque()

    def pick(self, processes: list[Process], current_pid: int | None, quantum: int) -> int | None:
        runnable = [p for p in processes if p.state in {ProcessState.READY, ProcessState.RUNNING}]
        runnable_ids = {p.pid for p in runnable}
        self.rotation = deque(pid for pid in self.rotation if pid in runnable_ids)

        for process in sorted(runnable, key=lambda p: p.created_tick):
            if process.pid not in self.rotation:
                self.rotation.append(process.pid)

        if not self.rotation:
            return None

        current = next((p for p in runnable if p.pid == current_pid), None)
        if current and current.state == ProcessState.RUNNING and current.quantum_used < quantum:
            return current.pid

        if current and current.pid in self.rotation:
            while self.rotation and self.rotation[0] != current.pid:
                self.rotation.rotate(-1)
            self.rotation.rotate(-1)

        return self.rotation[0]

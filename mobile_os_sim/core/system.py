from __future__ import annotations

import random
import threading
from collections import deque

from mobile_os_sim.core.models import Process, ProcessState, ResourceLock
from mobile_os_sim.core.scheduler import FIFOScheduler, RoundRobinScheduler


class MobileOS:
    TOTAL_RAM_MB = 4096
    RR_QUANTUM = 2
    LOG_LIMIT = 120
    APP_CATALOG = [
        ("Chat", 220, 2),
        ("Maps", 540, 3),
        ("Camera", 700, 4),
        ("Music", 260, 1),
        ("Browser", 620, 3),
        ("Gallery", 320, 2),
        ("Mail", 240, 2),
        ("Store", 480, 2),
        ("Notes", 180, 1),
        ("Video", 900, 4),
    ]

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.tick = 0
            self.next_pid = 1
            self.processes: dict[int, Process] = {}
            self.files: dict[str, str] = {}
            self.logs: deque[str] = deque(maxlen=self.LOG_LIMIT)
            self.locks: dict[str, ResourceLock] = {
                "camera": ResourceLock("camera"),
                "storage": ResourceLock("storage"),
                "audio": ResourceLock("audio"),
            }
            self.scheduler_mode = "FIFO"
            self.current_pid: int | None = None
            self.fifo_scheduler = FIFOScheduler()
            self.rr_scheduler = RoundRobinScheduler()
            self.log("System", "Simulator reset")

    def snapshot(self) -> dict:
        with self._lock:
            used_ram = sum(p.memory_mb for p in self.processes.values() if p.state != ProcessState.TERMINATED)
            processes = sorted(self.processes.values(), key=lambda p: p.pid)
            return {
                "tick": self.tick,
                "scheduler": self.scheduler_mode,
                "quantum": self.RR_QUANTUM,
                "current_pid": self.current_pid,
                "ram_total_mb": self.TOTAL_RAM_MB,
                "ram_used_mb": used_ram,
                "ram_percent": round((used_ram / self.TOTAL_RAM_MB) * 100, 1),
                "processes": [p.to_dict() for p in processes],
                "files": [{"name": name, "content": content} for name, content in sorted(self.files.items())],
                "locks": [lock.to_dict() for lock in self.locks.values()],
                "logs": list(self.logs),
            }

    def log(self, component: str, message: str) -> None:
        self.logs.append(f"[T{self.tick:03d}] [{component}] {message}")

    def open_app(self, name: str | None = None) -> None:
        with self._lock:
            app_name, memory_mb, priority = self._choose_app(name)
            pid = self.next_pid
            self.next_pid += 1
            process = Process(
                pid=pid,
                name=app_name,
                memory_mb=memory_mb,
                priority=priority,
                state=ProcessState.NEW,
                created_tick=self.tick,
            )
            self.processes[pid] = process
            self.log("Process", f"Opened {app_name} as P{pid} ({memory_mb} MB, priority {priority})")
            self._transition_process(process, ProcessState.READY, "app opened")
            self._handle_memory_pressure(context=f"opening P{pid}")
            self._reschedule("new app created")

    def close_app(self, pid: int | None = None) -> None:
        with self._lock:
            process = self._select_process(pid, preferred_states=None)
            if not process:
                self.log("Process", "Close request ignored: no process available")
                return
            self._terminate_process(process, "user closed app")
            self._reschedule("process closed")

    def switch_scheduler(self) -> None:
        with self._lock:
            self.scheduler_mode = "ROUND_ROBIN" if self.scheduler_mode == "FIFO" else "FIFO"
            for process in self.processes.values():
                process.quantum_used = 0
            self.log("Scheduler", f"Mode switched to {self.scheduler_mode}")
            self._reschedule("scheduler mode changed", force_switch=True)

    def simulate_file_io(self) -> None:
        with self._lock:
            process = self._select_process(preferred_states={ProcessState.RUNNING, ProcessState.READY})
            if not process:
                self.log("File", "File I/O request ignored: no runnable process")
                return

            filename = f"{process.name.lower()}_{process.pid}.txt"
            operation = random.choice(["create", "write", "read", "delete"])

            if operation == "create":
                self.files[filename] = f"boot log for P{process.pid}"
            elif operation == "write":
                self.files[filename] = self.files.get(filename, "") + f" | tick {self.tick}"
            elif operation == "read":
                self.files.setdefault(filename, f"cached content for P{process.pid}")
            elif operation == "delete":
                self.files.pop(filename, None)

            self.log("File", f"P{process.pid} started file operation ({operation} {filename})")
            self._block_process(process, 3, "file I/O", io_operation=f"{operation} {filename}")
            self._reschedule("file I/O blocked process", force_switch=True)

    def simulate_memory_pressure(self) -> None:
        with self._lock:
            process = self._select_process(preferred_states={ProcessState.RUNNING, ProcessState.READY})
            if not process:
                self.log("Memory", "Memory pressure ignored: no active process")
                return
            spike = random.randint(600, 1100)
            process.memory_mb += spike
            self.log("Memory", f"P{process.pid} requested +{spike} MB -> pressure triggered")
            self._handle_memory_pressure(context=f"pressure from P{process.pid}")
            self._reschedule("memory pressure handled")

    def simulate_lock_conflict(self) -> None:
        with self._lock:
            runnable = self._runnable_processes()
            if len(runnable) < 2:
                self.log("Lock", "Lock conflict ignored: open at least two apps")
                return

            owner = runnable[0]
            waiter = runnable[1]
            resource = self.locks["storage"]

            if resource.owner_pid != owner.pid:
                self._acquire_lock(owner, resource.name)

            self._request_lock(waiter, resource.name)
            self._reschedule("lock conflict blocked process", force_switch=True)

    def trigger_failure_scenario(self) -> None:
        with self._lock:
            process = self._select_process(preferred_states={ProcessState.RUNNING, ProcessState.READY, ProcessState.BLOCKED})
            if not process:
                self.log("Failure", "Failure scenario ignored: no process available")
                return
            self.log("Failure", f"Controlled crash injected into P{process.pid}")
            self._terminate_process(process, "process crash")
            self._reschedule("failure scenario", force_switch=True)

    def simulate_priority_inversion(self) -> None:
        with self._lock:
            self._clear_active_processes()

            low = self._spawn_custom_process("SyncService", 280, priority=1)
            medium = self._spawn_custom_process("VideoEncoder", 650, priority=2)
            high = self._spawn_custom_process("EmergencyCall", 310, priority=5)

            self._acquire_lock(low, "camera")
            self._request_lock(high, "camera")
            low.inherited_priority = high.effective_priority
            self.log(
                "Priority",
                f"Inversion detected: P{high.pid} (high) waiting for camera held by P{low.pid} (low)",
            )
            self.log(
                "Priority",
                f"Priority inheritance applied: P{low.pid} boosted from {low.priority} -> {low.effective_priority}",
            )

            medium.state = ProcessState.READY
            self._reschedule("priority inversion scenario", force_switch=True)

    def advance_tick(self) -> None:
        with self._lock:
            self.tick += 1
            self._update_blocked_processes()
            self._handle_priority_inheritance_release()
            self._reschedule("timer tick")
            self._run_current_process()

    def _choose_app(self, requested_name: str | None) -> tuple[str, int, int]:
        if requested_name:
            for app in self.APP_CATALOG:
                if app[0].lower() == requested_name.lower():
                    return app
        return random.choice(self.APP_CATALOG)

    def _spawn_custom_process(self, name: str, memory_mb: int, priority: int) -> Process:
        pid = self.next_pid
        self.next_pid += 1
        process = Process(
            pid=pid,
            name=name,
            memory_mb=memory_mb,
            priority=priority,
            state=ProcessState.READY,
            created_tick=self.tick,
        )
        self.processes[pid] = process
        self.log("Process", f"Opened {name} as P{pid} ({memory_mb} MB, priority {priority})")
        return process

    def _handle_memory_pressure(self, context: str) -> None:
        while self._used_ram() > self.TOTAL_RAM_MB:
            victim = self._memory_pressure_victim()
            if not victim:
                break
            self.log(
                "Memory",
                f"RAM full -> Killing P{victim.pid} (priority={victim.effective_priority}, lowest-priority candidate, selected by pressure handler)",
            )
            released_mb = victim.memory_mb
            self._terminate_process(victim, "memory pressure")
            self.log("Memory", f"Released {released_mb} MB from P{victim.pid}")

    def _memory_pressure_victim(self) -> Process | None:
        candidates = [
            p
            for p in self.processes.values()
            if p.state != ProcessState.TERMINATED
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda p: (
                p.state == ProcessState.RUNNING,
                p.effective_priority,
                p.cpu_ticks,
                -p.memory_mb,
            )
        )
        return candidates[0]

    def _used_ram(self) -> int:
        return sum(p.memory_mb for p in self.processes.values() if p.state != ProcessState.TERMINATED)

    def _select_process(
        self,
        pid: int | None = None,
        preferred_states: set[ProcessState] | None = None,
    ) -> Process | None:
        if pid is not None:
            process = self.processes.get(int(pid))
            if process and process.state != ProcessState.TERMINATED:
                return process
            return None

        candidates = [
            p for p in self.processes.values()
            if p.state != ProcessState.TERMINATED
            and (preferred_states is None or p.state in preferred_states)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: (p.state != ProcessState.RUNNING, -p.effective_priority, p.pid))
        return candidates[0]

    def _runnable_processes(self) -> list[Process]:
        runnable = [
            p for p in self.processes.values()
            if p.state in {ProcessState.READY, ProcessState.RUNNING}
        ]
        runnable.sort(key=lambda p: (-p.effective_priority, p.created_tick, p.pid))
        return runnable

    def _acquire_lock(self, process: Process, resource_name: str) -> None:
        resource = self.locks[resource_name]
        if resource.owner_pid is None:
            resource.owner_pid = process.pid
            process.held_resources.add(resource_name)
            self.log("Lock", f"P{process.pid} acquired {resource_name}")

    def _request_lock(self, process: Process, resource_name: str) -> None:
        resource = self.locks[resource_name]
        if resource.owner_pid is None:
            self._acquire_lock(process, resource_name)
            return

        owner = self.processes.get(resource.owner_pid)
        if owner and process.effective_priority > owner.effective_priority:
            owner.inherited_priority = process.effective_priority
        if process.pid not in resource.wait_queue:
            resource.wait_queue.append(process.pid)
        self._block_process(process, 4, f"lock wait on {resource_name}")
        process.waiting_resource = resource_name
        self.log("Lock", f"P{process.pid} BLOCKED waiting for {resource_name} (held by P{resource.owner_pid})")

    def _release_lock(self, process: Process, resource_name: str) -> None:
        resource = self.locks[resource_name]
        if resource.owner_pid != process.pid:
            return

        resource.owner_pid = None
        process.held_resources.discard(resource_name)
        had_inherited_priority = process.inherited_priority is not None
        process.inherited_priority = None

        while resource.wait_queue:
            next_pid = resource.wait_queue.pop(0)
            waiter = self.processes.get(next_pid)
            if not waiter or waiter.state == ProcessState.TERMINATED:
                continue
            self.log("Lock", f"{resource_name} released by P{process.pid} -> waking P{waiter.pid}")
            self._transition_process(waiter, ProcessState.READY, f"{resource_name} available")
            waiter.block_reason = None
            waiter.blocked_ticks_remaining = 0
            waiter.waiting_resource = None
            resource.owner_pid = waiter.pid
            waiter.held_resources.add(resource_name)
            self.log("Lock", f"P{waiter.pid} acquired {resource_name} after wait")
            if had_inherited_priority:
                self.log("Priority", f"Resource released -> P{process.pid} priority restored")
            break
        else:
            self.log("Lock", f"{resource_name} released by P{process.pid}")
            if had_inherited_priority:
                self.log("Priority", f"Resource released -> P{process.pid} priority restored")

    def _block_process(self, process: Process, ticks: int, reason: str, io_operation: str | None = None) -> None:
        previous_state = process.state
        process.state = ProcessState.BLOCKED
        process.blocked_ticks_remaining = ticks
        process.block_reason = reason
        process.io_operation = io_operation
        process.quantum_used = 0
        if self.current_pid == process.pid:
            self.current_pid = None
        if io_operation:
            self.log("File", f"P{process.pid} BLOCKED due to file I/O")
            self.log("Process", f"P{process.pid} BLOCKED due to file I/O")
        elif reason.startswith("lock wait"):
            self.log("Process", f"P{process.pid} BLOCKED due to lock conflict")
        else:
            self.log("Process", f"P{process.pid} BLOCKED due to {reason}")
        self.log("Process", f"P{process.pid} transitioned {previous_state.value} -> BLOCKED ({reason})")

    def _terminate_process(self, process: Process, reason: str) -> None:
        for resource_name in list(process.held_resources):
            self._release_lock(process, resource_name)

        for resource in self.locks.values():
            if process.pid in resource.wait_queue:
                resource.wait_queue = [pid for pid in resource.wait_queue if pid != process.pid]

        previous_state = process.state
        released_mb = process.memory_mb
        process.state = ProcessState.TERMINATED
        process.blocked_ticks_remaining = 0
        process.block_reason = reason
        process.waiting_resource = None
        process.io_operation = None
        process.quantum_used = 0
        if self.current_pid == process.pid:
            self.current_pid = None
        if reason == "process crash":
            self.log("Failure", f"P{process.pid} terminated due to crash")
        self.log("Process", f"P{process.pid} transitioned {previous_state.value} -> TERMINATED ({reason})")
        if reason != "memory pressure":
            self.log("Memory", f"Released {released_mb} MB from P{process.pid}")

    def _reschedule(self, reason: str, force_switch: bool = False) -> None:
        scheduler = self.fifo_scheduler if self.scheduler_mode == "FIFO" else self.rr_scheduler
        current_process = self.processes.get(self.current_pid) if self.current_pid else None

        if current_process and current_process.state == ProcessState.RUNNING and force_switch:
            self._transition_process(current_process, ProcessState.READY, reason)
            current_process.quantum_used = 0

        chosen_pid = scheduler.pick(list(self.processes.values()), self.current_pid, self.RR_QUANTUM)
        if chosen_pid is None:
            if self.current_pid is not None:
                self.log("Scheduler", f"CPU idle after {reason}")
            self.current_pid = None
            return

        if chosen_pid != self.current_pid:
            previous = f"P{self.current_pid}" if self.current_pid else "IDLE"
            mode_reason = self._scheduler_reason(reason)
            self.log("Scheduler", f"Switched {previous} -> P{chosen_pid} ({self.scheduler_mode}, {mode_reason})")

        for process in self.processes.values():
            if process.state == ProcessState.RUNNING and process.pid != chosen_pid:
                self._transition_process(process, ProcessState.READY, "preempted by scheduler")
                process.quantum_used = 0

        chosen = self.processes[chosen_pid]
        if chosen.state == ProcessState.READY:
            self.log("Scheduler", f"Selected P{chosen.pid} from READY queue")
            self._transition_process(chosen, ProcessState.RUNNING, "selected by scheduler")
        self.current_pid = chosen_pid

    def _run_current_process(self) -> None:
        if self.current_pid is None:
            return
        process = self.processes.get(self.current_pid)
        if not process or process.state != ProcessState.RUNNING:
            return

        process.cpu_ticks += 1
        process.quantum_used += 1

        if self.scheduler_mode == "ROUND_ROBIN" and process.quantum_used >= self.RR_QUANTUM:
            self._transition_process(process, ProcessState.READY, "Round Robin quantum expired")
            process.quantum_used = 0
            self._reschedule("round robin quantum", force_switch=True)

    def _update_blocked_processes(self) -> None:
        for process in self.processes.values():
            if process.state != ProcessState.BLOCKED:
                continue
            process.blocked_ticks_remaining -= 1
            if process.blocked_ticks_remaining > 0:
                continue

            if process.waiting_resource:
                resource = self.locks[process.waiting_resource]
                if resource.owner_pid is not None:
                    process.blocked_ticks_remaining = 1
                    continue

            self._transition_process(process, ProcessState.READY, "I/O completed" if process.io_operation else "unblocked")
            process.block_reason = None
            if process.io_operation:
                self.log("File", f"File operation completed -> P{process.pid} moved to READY")
            process.io_operation = None

    def _handle_priority_inheritance_release(self) -> None:
        for process in self.processes.values():
            if process.state == ProcessState.TERMINATED:
                continue
            if process.inherited_priority and process.cpu_ticks >= 2 and process.held_resources:
                for resource_name in list(process.held_resources):
                    self._release_lock(process, resource_name)

    def _clear_active_processes(self) -> None:
        for process in list(self.processes.values()):
            if process.state != ProcessState.TERMINATED:
                self._terminate_process(process, "scenario reset")

    def _transition_process(self, process: Process, new_state: ProcessState, reason: str) -> None:
        if process.state == new_state:
            return
        previous_state = process.state
        process.state = new_state
        self.log("Process", f"P{process.pid} transitioned {previous_state.value} -> {new_state.value} ({reason})")

    def _scheduler_reason(self, reason: str) -> str:
        reasons = {
            "round robin quantum": "quantum expired",
            "file I/O blocked process": "file I/O blocked running process",
            "lock conflict blocked process": "lock conflict blocked process",
            "memory pressure handled": "memory pressure handled",
            "scheduler mode changed": "mode changed",
            "new app created": "new app ready",
            "process closed": "process terminated",
            "failure scenario": "failure handled",
            "priority inversion scenario": "priority inheritance active",
            "timer tick": "timer tick",
        }
        return reasons.get(reason, reason)

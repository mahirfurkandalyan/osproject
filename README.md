# Mini Mobile OS Simulator

Interactive smartphone-style operating system simulator for the Operating Systems course project.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Demo Flow

1. Click `Open App` several times to create mobile app processes.
2. Switch between `FIFO` and `Round Robin` to compare scheduler behavior.
3. Trigger `Simulate File I/O` to block a process and watch the scheduler switch.
4. Trigger `Simulate Lock Conflict` to block a process on a shared resource.
5. Trigger `Simulate Memory Pressure` until RAM recovery kills lower-priority apps.
6. Use `Priority Inversion` to show inheritance in the logs and priority field.
7. Use `Trigger Failure Scenario` for a controlled process crash.
8. Use `Reset System` to return to a clean state.

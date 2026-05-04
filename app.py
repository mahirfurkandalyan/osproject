from flask import Flask, jsonify, render_template, request

from mobile_os_sim.core.system import MobileOS


app = Flask(__name__)
os_sim = MobileOS()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    os_sim.advance_tick()
    return jsonify(os_sim.snapshot())


@app.post("/api/apps/open")
def open_app():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    os_sim.open_app(name=name)
    return jsonify(os_sim.snapshot())


@app.post("/api/apps/close")
def close_app():
    payload = request.get_json(silent=True) or {}
    pid = payload.get("pid")
    os_sim.close_app(pid)
    return jsonify(os_sim.snapshot())


@app.post("/api/scheduler/switch")
def switch_scheduler():
    os_sim.switch_scheduler()
    return jsonify(os_sim.snapshot())


@app.post("/api/events/file-io")
def file_io():
    os_sim.simulate_file_io()
    return jsonify(os_sim.snapshot())


@app.post("/api/events/memory-pressure")
def memory_pressure():
    os_sim.simulate_memory_pressure()
    return jsonify(os_sim.snapshot())


@app.post("/api/events/lock-conflict")
def lock_conflict():
    os_sim.simulate_lock_conflict()
    return jsonify(os_sim.snapshot())


@app.post("/api/events/failure")
def failure():
    os_sim.trigger_failure_scenario()
    return jsonify(os_sim.snapshot())


@app.post("/api/events/priority-inversion")
def priority_inversion():
    os_sim.simulate_priority_inversion()
    return jsonify(os_sim.snapshot())


@app.post("/api/reset")
def reset_system():
    os_sim.reset()
    return jsonify(os_sim.snapshot())


if __name__ == "__main__":
    app.run(debug=True)

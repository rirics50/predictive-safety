[README.md](https://github.com/user-attachments/files/32563372/README.md)
# A-Z Predictive Safety System

**BuildOdoo 2026 (Heriot-Watt Tech Club × Odoo)** — Track 2: AI for Good, aligned with the UAE National Strategy for Artificial Intelligence 2031.

## The Problem
In high-risk sectors like oil and gas, unpredictable chemical reactions and pressure drops lead to catastrophic equipment failures, environmental hazards, and loss of life. Traditional ERP systems are purely reactive — they log equipment damage and issue repair tickets only *after* a disaster has already occurred.

## The Solution
An autonomous AI safety agent that bridges Operational Technology (OT) and Information Technology (IT). By continuously comparing live physical telemetry against equipment-specific engineering safety limits, the system predicts critical failures before they happen — automatically shutting down the plant while simultaneously triggering a company-wide crisis management workflow.

## Architecture

```
CoppeliaSim (OT)  →  ROS 2  →  MATLAB (Analytical Brain)  →  Odoo (Command Center)
   3D digital twin     bridge     SAFE / WARNING / CRITICAL      shutdown + workflows
```

| Layer | Role |
|---|---|
| **CoppeliaSim** | 3D digital twin of the process (Feed → Reactor → Flash Drum → Pipeline → ESD Valve). Publishes live telemetry, hosts the controllable emergency shutdown valve. |
| **ROS 2** | Communication layer routing telemetry between CoppeliaSim, MATLAB, and Odoo via `rosbridge_websocket` (port 9090). |
| **MATLAB** | Engineering/safety engine. Callable functions (e.g. `check_reactor`, `check_pipeline`) combine live telemetry with equipment specs to evaluate safety envelopes, returning SAFE / WARNING / CRITICAL. |
| **Odoo** | UI, Equipment Library, monitoring dashboard, and emergency management. On CRITICAL: halts production (Quality), opens a Maintenance ticket, dispatches Field Service, scraps/reorders materials (Inventory & Purchase), and notifies shift workers (Discuss). |

## Demo Scenarios
- **Primary:** Feed disturbance → reactor temp/pressure deviates → MATLAB flags CRITICAL → Odoo triggers ESD valve closure → maintenance record created.
- **Secondary:** Pipeline pressure spike → MATLAB detects envelope breach → CRITICAL → ESD valve closes → emergency/maintenance response.

## Repo Structure
The repo root is the `predictive_safety` Odoo module itself (clone it into a folder named `predictive_safety` on your Odoo `addons_path`):
```
├── __manifest__.py       # Odoo module manifest
├── models/               # Pipeline equipment, pressure history, Force Shutdown / Manual Reset, Discuss alerts
├── views/                # Pipeline form (status badges, pressure chart), list and graph views
├── security/             # Access rights
├── safety_listener.py    # ROS 2 ↔ Odoo bridge: latching auto-shutdown, pushes readings into Odoo
├── check_db.py           # Helper: lists Odoo databases
├── coppeliasim/          # 3D scene + Lua control script (paste into the /Outflow_Pipe child script)
├── ros_bridge/           # ZMQ ↔ ROS 2 relay script (runs in the ROS 2 Docker container)
├── matlab/               # (planned) Safety-envelope functions (check_reactor, check_pipeline, etc.)
└── docs/                 # (planned) Architecture diagrams, notes
```

`safety_listener.py` reads `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME` and `ODOO_PASSWORD` from the environment (defaults: local demo instance).

## Team
- **Noel** — MATLAB safety-envelope engineering logic
- **Riya** — CoppeliaSim, ROS bridge, Odoo integration

## Status
🚧 Work in progress — see commit history for current integration state.

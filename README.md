# CapCo: Automating Carla-Apollo Co-Simulation and Scenario Fuzzing

**CapCo** is an open-source framework that automates the closed-loop co-simulation between the **Carla simulator** and the **Apollo autonomous driving system**. It streamlines scenario-based testing and enables systematic evaluation of ADS safety across multiple versions of Apollo.

> 🔧 Designed for ADS developers and researchers, CapCo simplifies the setup, execution, and analysis of co-simulation tests, with support for fuzzing strategies, scenario risk control, and batch evaluation.

---

## 🔍 Key Features

- 🔄 **Closed-Loop Carla-Apollo Co-Simulation**  
  Automates simulation lifecycle: scenario launch, Apollo runtime configuration, and synchronized execution.

- 🧠 **Fuzzing-Driven Testing**  
  Includes multiple scenario search strategies (e.g., PSO, GA).

- 🧰 **Modular Architecture**  
  Supports extension for new scenario formats, ADS models, metrics, and search strategies.

- 🖥️ **Lightweight Interactive UI**  
  Optional frontend to configure runs and visualize scenario/test results.

---

## 🧱 System Overview

```
+--------------------------+
|    Web Interface (UI)   |  <-- Configure scenario & Apollo, monitor results
+--------------------------+
            |
            v
+--------------------------+
|   Backend Controller    |  <-- Manages lifecycle, search, data collection
+--------------------------+
            |
            v
+--------------------------+
| Carla + Apollo Runtime  |  <-- Co-simulation engine
+--------------------------+
            |
            v
+--------------------------+
|      Metric Logger      |  <-- Collision stats, TTC, trajectory, logs
+--------------------------+
            |
            v
+--------------------------+
|     Report Generator    |  <-- CSV + chart export, scoring
+--------------------------+
```

---

## 🚀 Getting Started

### Prerequisites
- Docker (required)
- NVIDIA GPU + CUDA drivers
- Ubuntu 20.04/22.04

### Quick Setup
```bash
# Clone the repo
git clone https://github.com/TayYim/CapCo.git
cd CapCo
```

Set up dependencies:
```bash
cd dependencies

git clone https://github.com/TayYim/scenario_runner.git -b capco

git clone https://github.com/TayYim/leaderboard.git -b capco
```

Install requirements:
```bash
pip install -r requirements.txt
```

Optional: create Python environment
```bash
conda create -n capco python=3.12
conda activate capco
```

Planned Docker integration:
```bash
docker-compose up
```
> Manual setup is also supported. See `docs/install.md` for detailed instructions.

---

## 🧪 Usage Workflow

1. **Select Scenario & Apollo Version**
2. **Choose Risk Level / Search Strategy** (e.g., PSO, GA)
3. **Configure Test Loop**: Set number of runs, mutation budget
4. **Launch Co-Simulation**: Each scenario is tested with Apollo
5. **Record Results**: Collisions, TTC, distance, score
6. **Generate Report**: CSV logs + charts + safety ranking

---

## 📁 Directory Structure
```
Capco/
├── src/                      # Main source code
│   ├── frontend/             # React web UI (localhost:3000)
│   ├── backend/              # FastAPI server (localhost:8089)
│   ├── simulation/           # CARLA simulation runner & scripts
│   └── utils/                # Shared utilities
├── dependencies/             # External dependencies
│   ├── leaderboard/          # CARLA Leaderboard scenarios
│   └── scenario_runner/      # CARLA Scenario Runner
├── config/                   # Configuration files
│   ├── parameter_ranges.yaml # Fuzzing parameter definitions
│   └── apollo_config.yaml    # Apollo agent configuration
├── docs/                     # Documentation
├── output/                   # Experiment results & logs
├── experiments.db            # SQLite database
├── env_config.json           # Environment configuration
├── requirements.txt          # Python dependencies
└── README.md
```

<!-- ---

## 🎥 Demo and Materials

- Screencast: [TBD link](#)
- Sample Report: [report_example.pdf](./reports/report_example.pdf)
- Paper: See [ASE 2025 Tool Demo Submission](#) -->



---

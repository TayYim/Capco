# Carlo: Automating Apollo-Co-Simulation and Scenario Fuzzing in Carla

**Carlo** is an open-source tool that automates the co-simulation of the **Apollo autonomous driving system** within the **Carla simulator**, enabling iterative scenario testing with customizable fuzzing and evaluation pipelines.

> 🚗 Built for ADS researchers and engineers, Carlo lets you execute, fuzz, and evaluate traffic scenarios across different Apollo versions in a reproducible and extensible framework.

---

## 🎯 Features

- 🔁 **Apollo-Carla Co-Simulation**  
  Seamless integration of Apollo with Carla, supporting multi-version Apollo testing (e.g., v7.0, v8.0, v9.0).

- 🧪 **Scenario-Based Testing**  
  Supports scenarios defined in OpenScenario or BehaviorTree formats, with automatic loading and execution.

- 🧬 **Scenario Fuzzing & Mutation**  
  Enables iterative testing via user-selectable searchers (e.g., Random, PSO, GA) to mutate scenario parameters.

- 📊 **Evaluation and Reporting**  
  Collects runtime metrics (e.g., collisions, time-to-collision, trajectory) and exports structured evaluation reports (CSV + visualizations).

- 🧑‍💻 **Interactive UI**  
  Web-based interface for scenario configuration, Apollo version selection, progress tracking, and result visualization.

---

## 🧱 System Architecture

```
+--------------------------+
|   Web Frontend (UI)     |  <-- Scenario config, fuzzer choice, run logs, charts
+--------------------------+
            |
            v
+--------------------------+
| Backend Controller (API)|  <-- Launch Carla + Apollo, loop over iterations
+--------------------------+
            |
            v
+--------------------------+
| Carla + Apollo Runtime  |  <-- Co-simulation per scenario
+--------------------------+
            |
            v
+--------------------------+
|   Metrics Collector     |  <-- Log parsing, performance metrics
+--------------------------+
            |
            v
+--------------------------+
|      Report Engine      |  <-- CSV export, visual charts, summary
+--------------------------+
```

---

## 🚀 Getting Started

### Prerequisites

- Docker (required)
- NVIDIA GPU + CUDA drivers
- Ubuntu 20.04/22.04

### Quick Setup (in development)

```bash
# Clone the repository
git clone https://github.com/TayYim/Carlo.git
cd carlo
```

Then go to dependencies and install the requirements
```
cd dependencies

git clone https://github.com/TayYim/scenario_runner.git -b carlo

git clone https://github.com/TayYim/leaderboard.git -b carlo
```

Then install the requirements using the python environment for Carla
```
pip install -r requirements.txt
```

Also need to create a new python environment for the project
```
conda create -n carlo python=3.12
conda activate carlo
```



```
# Launch system using Docker Compose (planned)
docker-compose up
```

> The Docker image bundles Carla, Apollo, and required bridges. See `docs/install.md` for manual setup if needed.

---

## 🧪 Usage Workflow

1. **Select Apollo Version & Scenario**
2. **Choose Searcher**: PSO, GA, or Random
3. **Configure Fuzzing Loop**: Set number of iterations
4. **Launch Simulation**: Each scenario is executed in Carla with Apollo control
5. **Collect Results**: Reports and charts generated per iteration
6. **Download Reports**: Raw logs + summaries + CSV/plot files

---

## 📁 Project Structure

```
carlo/
├── frontend/           # Web UI (Streamlit or Flask+React)
├── backend/            # Core controller logic
├── runner/             # Carla-Apollo runtime setup
├── fuzz/               # Scenario searchers (GA, PSO, etc.)
├── evaluator/          # Metric computation, scoring
├── scenarios/          # Sample scenarios in OpenScenario or BT
├── reports/            # Logs, charts, exportable outputs
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 📽️ Screencast & Demo

- Screencast (coming soon): [YouTube Link or local `demo.mp4`](#)
- Sample test report: [report_example.pdf](./reports/report_example.pdf)

---

## 🔓 License

MIT License. See [LICENSE](./LICENSE) for details.

---

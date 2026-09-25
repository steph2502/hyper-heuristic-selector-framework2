# University Timetabling Optimisation System 🎓

A web-based university course timetabling system powered by a **Selection Hyper-Heuristic framework** that dynamically selects between **Ant Colony Optimization (ACO)** and **Particle Swarm Optimization (PSO)** to generate optimized academic timetables.

The system combines **combinatorial optimization, metaheuristic algorithms, and web-based software engineering** to automate the generation of university course timetables while considering hard and soft scheduling constraints.

---

## Overview

University course timetabling is a complex combinatorial optimization problem involving the allocation of courses to available **time slots and classrooms** while satisfying institutional constraints.

As the number of courses, rooms, students, and scheduling requirements increases, the number of possible timetable configurations grows rapidly. This makes manual scheduling difficult and motivates the use of optimization techniques and metaheuristic approaches. University course timetabling is widely treated as an NP-hard optimization problem in the research literature.

This project implements a **Selection Hyper-Heuristic** approach.

Rather than relying exclusively on one optimization algorithm, the framework treats **ACO and PSO as low-level heuristics** and allows a higher-level controller to select between them during the optimization process.

```text
                    Scheduling Problem
                           │
                           ▼
                  Selection Hyper-Heuristic
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
       Ant Colony Optimization   Particle Swarm Optimization
              (ACO)                      (PSO)
                │                     │
                └──────────┬──────────┘
                           ▼
                  Candidate Timetable
                           │
                           ▼
                    Fitness Evaluation
                           │
                           ▼
                   Optimized Timetable
```

The goal is not simply to generate a timetable, but to provide a system that can **adapt its search strategy based on the scheduling problem and the performance of the available heuristics**.

---

# Key Features

### 📂 Dataset Upload

Users can provide timetable datasets containing the information required to generate a schedule.

The system processes the uploaded data and prepares it for optimization.

---

### ⚙️ Algorithm Selection

The system provides a Selection Hyper-Heuristic framework capable of working with:

* Ant Colony Optimization (ACO)
* Particle Swarm Optimization (PSO)

The controller determines which optimization strategy should be applied during the search process.

---

### 🧠 Hyper-Heuristic Optimization

Instead of hard-coding a single optimization technique, the system introduces a higher-level controller responsible for selecting between available optimization strategies.

This creates a two-level optimization structure:

```text
High-Level
Selection Hyper-Heuristic
        │
        ├───────────────┐
        ▼               ▼
       ACO             PSO
   Low-Level         Low-Level
   Heuristic         Heuristic
        │               │
        └───────┬───────┘
                ▼
         Timetable Solution
```

---

### 📊 Fitness Evaluation

Generated timetables are evaluated using constraint-based fitness measures.

The system considers:

* Hard constraint violations
* Soft constraint violations
* Overall fitness
* Runtime

This allows different optimization approaches to be compared using measurable results.

---

### 📅 Timetable Generation

After optimization, the system generates a timetable that maps courses to available:

* Time slots
* Classrooms

The resulting timetable can then be visualized through the web interface.

---

### 📈 Result Visualization

The system presents optimization results so that users can inspect the generated timetable and compare algorithm performance.

---

# Problem Definition

The university timetable problem can be represented as an allocation problem.

Given:

* A set of courses
* A set of available rooms
* A set of time slots
* Scheduling constraints
* Optimization objectives

the system attempts to find an assignment:

```text
Course → Time Slot → Room
```

such that hard constraints are satisfied while soft constraint violations are minimized.

A simplified representation is:

```text
Courses
   │
   ├── CSC411
   ├── CSC413
   ├── CSC416
   ├── CSC431
   ├── CSC433
   ├── EDS411
   ├── TMC411
   ├── DLD211
   ├── MIS415
   └── CSC415
        │
        ▼
   Optimization
        │
        ├── Time Slots
        └── Rooms
        │
        ▼
   Generated Timetable
```

---

# Hard and Soft Constraints

The system distinguishes between **hard constraints** and **soft constraints**.

## Hard Constraints

Hard constraints represent conditions that should not be violated because they would make a timetable infeasible.

Examples include:

* A room cannot host two courses simultaneously.
* A course cannot be scheduled in two locations at the same time.
* A time slot cannot contain conflicting assignments.
* Required scheduling resources must be available.

Hard constraint violations therefore carry a higher penalty during fitness evaluation.

---

## Soft Constraints

Soft constraints represent preferences or desirable scheduling properties.

Unlike hard constraints, they may be violated when necessary, but the optimization process attempts to minimize their occurrence.

Examples can include:

* Avoiding undesirable scheduling arrangements.
* Improving the distribution of courses.
* Reducing unnecessary scheduling conflicts.
* Producing a more balanced timetable.

The distinction between hard and soft constraints is important because a timetable with fewer overall violations is not necessarily better if it violates critical hard constraints.

---

# Selection Hyper-Heuristic

## What is a Hyper-Heuristic?

A hyper-heuristic is a higher-level search strategy that operates over a collection of heuristics.

Instead of directly solving the problem using one algorithm, the hyper-heuristic determines **which heuristic should be used and when**.

This approach has been studied extensively in educational timetabling, including selection hyper-heuristics that dynamically choose among low-level heuristics during the search process.

The architecture of this project follows the same general idea:

```text
                 Problem Instance
                       │
                       ▼
              Selection Controller
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
         ACO                       PSO
          │                         │
          └────────────┬────────────┘
                       ▼
                Candidate Solution
                       │
                       ▼
                Fitness Evaluation
                       │
                       ▼
                 Search Feedback
                       │
                       └──────► Controller
```

The controller therefore operates at a higher level than ACO and PSO.

---

# Ant Colony Optimization

**Ant Colony Optimization (ACO)** is a population-based metaheuristic inspired by the behaviour of ants searching for paths.

In the context of this project, ACO constructs candidate timetable solutions while using pheromone information to influence future solution construction.

A simplified process is:

```text
Initialize pheromone information
            │
            ▼
Construct candidate timetables
            │
            ▼
Evaluate timetable fitness
            │
            ▼
Update pheromone information
            │
            ▼
Repeat optimization
```

The pheromone mechanism allows the search process to retain information about promising solution components.

---

# Particle Swarm Optimization

**Particle Swarm Optimization (PSO)** is a population-based optimization technique inspired by collective behaviour in biological swarms.

PSO maintains a population of candidate solutions, represented as particles, and updates them based on their own search experience and information obtained from the population.

A simplified process is:

```text
Initialize particle population
            │
            ▼
Evaluate candidate solutions
            │
            ▼
Track best solutions
            │
            ▼
Update particle positions
            │
            ▼
Evaluate new solutions
            │
            ▼
Repeat optimization
```

For this project, PSO provides an alternative search strategy to ACO.

PSO-based hyper-heuristic approaches have also been explored in university course timetabling research.

---

# Why Use Multiple Heuristics?

Different optimization algorithms can behave differently depending on the structure of the problem instance.

A single algorithm may perform well on one scheduling configuration but less effectively on another.

The motivation behind the Selection Hyper-Heuristic framework is therefore to avoid making the entire system dependent on one optimization strategy.

```text
                 Scheduling Instance
                        │
                        ▼
                Hyper-Heuristic
                        │
             ┌──────────┴──────────┐
             │                     │
          ACO performs          PSO performs
          well here             well here
             │                     │
             └──────────┬──────────┘
                        ▼
                  Better Search
```

The broader research literature similarly explores hyper-heuristics as a way of selecting or sequencing lower-level heuristics for educational timetabling.

---

# System Architecture

The application follows a client-server architecture.

```text
┌───────────────────────────────┐
│           Frontend            │
│        React / JavaScript     │
│                               │
│ • Dataset Upload              │
│ • Configuration               │
│ • Algorithm Selection         │
│ • Results                     │
│ • Timetable Visualization     │
└───────────────┬───────────────┘
                │
                │ HTTP
                ▼
┌───────────────────────────────┐
│            Backend            │
│           FastAPI             │
│                               │
│ • API Endpoints               │
│ • Dataset Processing          │
│ • Optimization Controller     │
│ • Fitness Evaluation          │
│ • Timetable Generation        │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       Optimization Layer      │
│                               │
│ Selection Hyper-Heuristic     │
│          │                    │
│     ┌────┴────┐               │
│     ▼         ▼               │
│    ACO       PSO              │
└───────────────────────────────┘
```

---

# Technology Stack

## Frontend

* React
* JavaScript
* HTML
* CSS

The frontend provides the interface for uploading scheduling data, configuring the optimization process, and displaying generated results.

---

## Backend

* Python
* FastAPI

FastAPI provides the API layer responsible for receiving requests from the frontend, processing timetable data, running optimization algorithms, and returning results.

---

## Optimization

* Selection Hyper-Heuristic
* Ant Colony Optimization (ACO)
* Particle Swarm Optimization (PSO)
* Constraint-based fitness evaluation

---

# Application Workflow

The complete system workflow can be represented as:

```text
User
 │
 ▼
Upload Dataset
 │
 ▼
Dataset Validation
 │
 ▼
Problem Representation
 │
 ▼
Optimization Configuration
 │
 ▼
Selection Hyper-Heuristic
 │
 ├──────────────┐
 ▼              ▼
ACO             PSO
 │              │
 └───────┬──────┘
         ▼
 Fitness Evaluation
         │
         ▼
 Constraint Analysis
         │
         ▼
 Best Solution
         │
         ▼
 Timetable Visualization
```

---

# Dataset

The system was evaluated using timetable data based on the **ITC 2007** benchmark instances together with a university-specific dataset.

The International Timetabling Competition (ITC) 2007 is an established benchmark source for educational timetabling research, and its instances have been used extensively for evaluating optimization and hyper-heuristic approaches.

The university-specific configuration used in the project contains:

### Courses

The experimental university dataset includes 10 courses:

```text
CSC411
CSC413
CSC416
CSC431
CSC433
EDS411
TMC411
DLD211
MIS415
CSC415
```

### Time Slots

The timetable is generated across **4 available time slots**.

### Rooms

The scheduling problem includes **3 available rooms**.

---

# Optimization Objective

The primary objective is to generate a feasible timetable while minimizing constraint violations.

A simplified fitness formulation can be expressed as:

```text
Fitness =
    Hard Constraint Penalty
    +
    Soft Constraint Penalty
```

The optimization process attempts to minimize the resulting fitness value.

Therefore:

```text
Lower Fitness
      ↓
Fewer Constraint Violations
      ↓
More Suitable Timetable
```

The exact weighting of constraints depends on the fitness function implemented by the system.

---

# Experimental Results

The system was evaluated using four approaches:

1. Greedy
2. Ant Colony Optimization (ACO)
3. Particle Swarm Optimization (PSO)
4. Selection Hyper-Heuristic Controller

The results were evaluated using:

* Fitness
* Hard constraint violations
* Soft constraint violations
* Runtime

| Approach   | Fitness | Hard Constraints | Soft Constraints | Runtime (s) |
| ---------- | ------: | ---------------: | ---------------: | ----------: |
| Greedy     |  22,029 |            22.00 |            29.00 |        9.43 |
| ACO        |  21,368 |            21.67 |            34.33 |      173.52 |
| PSO        |  17,086 |            17.00 |            86.33 |       44.63 |
| Controller |  21,383 |            21.33 |            49.33 |       39.06 |

These results are included to demonstrate the behaviour of the implemented approaches under the project's experimental configuration.

The metrics should be interpreted together rather than using fitness alone, since runtime and the separate hard/soft constraint measures provide additional information about the generated schedules.

---

# Understanding the Results

The experiment demonstrates why timetable optimization involves multiple competing objectives.

For example, an algorithm may produce a lower aggregate fitness while still exhibiting a different distribution between hard and soft constraint violations or requiring substantially different computational time.

This makes timetable optimization more than simply finding the smallest numerical fitness value.

The system therefore exposes multiple evaluation metrics:

```text
                 Candidate Timetable
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Fitness      Hard Violations   Soft Violations
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                      Runtime
```

This provides a more useful basis for analysing the behaviour of each optimization strategy.

---

# API Architecture

The FastAPI backend provides the interface between the web application and the optimization engine.

A simplified request lifecycle is:

```text
HTTP Request
     │
     ▼
FastAPI Endpoint
     │
     ▼
Input Validation
     │
     ▼
Dataset Processing
     │
     ▼
Optimization Controller
     │
     ▼
ACO / PSO
     │
     ▼
Fitness Evaluation
     │
     ▼
Optimized Timetable
     │
     ▼
JSON Response
```

---

# Example System Response

A generated result can conceptually contain information such as:

```json
{
  "algorithm": "PSO",
  "fitness": 17086,
  "hard_constraints": 17,
  "soft_constraints": 86.33,
  "runtime": 44.63,
  "timetable": []
}
```

The actual response structure should match the implementation in the repository.

---

# Project Structure

The exact structure should reflect the repository, but the system is conceptually divided into:

```text
.
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── ...
│
├── backend/
│   ├── algorithms/
│   │   ├── aco/
│   │   ├── pso/
│   │   └── hyper_heuristic/
│   │
│   ├── controllers/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── main.py
│
├── datasets/
│
├── README.md
└── ...
```

> Update this section to match the actual repository structure before publishing the README.

---

# Installation

## Prerequisites

Make sure you have installed:

* Python 3.9+
* Node.js
* npm
* Git

---

# Backend Setup

Clone the repository:

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_NAME>
```

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

Install the backend dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API should then be available locally at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation can typically be accessed at:

```text
http://127.0.0.1:8000/docs
```

> Update the Uvicorn command if your `main.py` or application module uses a different path.

---

# Frontend Setup

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend can then communicate with the FastAPI backend through the configured API endpoint.

---

# Using the System

### Step 1 — Upload Dataset

Provide the timetable dataset through the web interface.

### Step 2 — Configure the Problem

Specify the relevant scheduling parameters and constraints.

### Step 3 — Select Optimization Strategy

Choose the available optimization mode supported by the application.

The Selection Hyper-Heuristic framework can use ACO and PSO as low-level optimization strategies.

### Step 4 — Generate Timetable

Start the optimization process.

The backend processes the dataset and executes the optimization workflow.

### Step 5 — Inspect Results

The system returns:

* Generated timetable
* Fitness score
* Hard constraint violations
* Soft constraint violations
* Runtime

### Step 6 — Visualize

The generated timetable is presented through the web interface for easier interpretation.

---

# Design Decisions

## Why FastAPI?

FastAPI was selected for the backend because the system needs a lightweight API layer capable of connecting the optimization engine to the web interface.

It also provides request validation and interactive API documentation, which simplifies development and testing.

---

## Why React?

React provides a component-based approach for building the interactive timetable interface.

This is useful for a system where users need to:

* Upload datasets
* Configure inputs
* Trigger optimization
* Monitor results
* Inspect timetable outputs

---

## Why ACO and PSO?

ACO and PSO represent two different population-based optimization strategies.

Using both creates an opportunity to investigate whether a higher-level selection mechanism can make use of their different search behaviours.

Rather than presenting ACO and PSO as universally superior algorithms, this project evaluates their behaviour within the specific timetabling problem and experimental configuration.

---

# Engineering Challenges

### Large Search Space

Even a relatively small timetable can produce a large number of possible assignments.

Adding additional courses, rooms, time slots, and constraints increases the complexity of the search problem.

---

### Constraint Handling

A generated timetable must satisfy multiple constraints simultaneously.

The optimization engine therefore needs a fitness mechanism capable of distinguishing between more and less desirable solutions.

---

### Algorithm Integration

ACO and PSO use different optimization mechanisms and solution representations.

Integrating them into a common framework required designing a shared interface through which the Selection Hyper-Heuristic could invoke and evaluate the available optimization strategies.

---

### Bridging Research and Software

The project was not implemented purely as an algorithmic experiment.

The optimization framework was exposed through a web application so that users could interact with the system through:

```text
Web Interface
      ↓
REST API
      ↓
Optimization Engine
      ↓
Timetable
      ↓
Visualization
```

This required translating an optimization research problem into a usable software system.

---

# Key Technical Concepts Demonstrated

This project demonstrates practical experience with:

* Combinatorial optimization
* Constraint optimization
* Metaheuristic algorithms
* Hyper-heuristics
* Ant Colony Optimization
* Particle Swarm Optimization
* Algorithm selection
* Fitness functions
* Search-space exploration
* REST API design
* FastAPI
* React
* Data processing
* Algorithm benchmarking
* Runtime analysis
* Experimental evaluation
* Data visualization

---

# Future Improvements

Potential future improvements include:

### Optimization

* Add additional low-level heuristics.
* Introduce adaptive learning for heuristic selection.
* Experiment with different move-acceptance strategies.
* Support multi-objective optimization.
* Improve constraint handling.
* Add parallel execution for algorithm comparisons.

### System

* Add persistent timetable storage.
* Add authentication and role-based access.
* Introduce timetable versioning.
* Add an administrator dashboard.
* Support multiple departments or faculties.
* Add timetable export to PDF/Excel.
* Add schedule conflict explanations.

### Engineering

* Add automated unit and integration tests.
* Add API documentation.
* Add structured logging.
* Add performance monitoring.
* Add CI/CD.
* Containerize the application with Docker.

---

# Research Context

University course timetabling is a well-established optimization problem involving the allocation of courses, rooms, and times while satisfying constraints. Recent literature continues to investigate metaheuristic and hyper-heuristic approaches because of the computational difficulty and large search spaces involved.

Selection hyper-heuristics specifically focus on choosing among lower-level heuristics, allowing the higher-level method to adapt the search strategy rather than depending entirely on one heuristic. This approach has been investigated in educational timetabling using both learning-based and iterative heuristic-selection strategies.

This project applies that general concept to a web-based university timetabling system by using **ACO and PSO as the available optimization strategies** and exposing the resulting optimization workflow through a FastAPI and React application.

---

# Project Goals

The project was developed with four main goals:

1. **Automate university timetable generation**
2. **Reduce constraint violations through optimization**
3. **Investigate the use of a Selection Hyper-Heuristic with ACO and PSO**
4. **Expose the optimization system through an interactive web application**

---

# Project Status

The system is a research-oriented prototype demonstrating the integration of optimization algorithms with a web-based software system.

It supports dataset-driven timetable generation, optimization, fitness evaluation, and timetable visualization.

---

# Author

**Stephanie Onwuagbaizu**

Computer Science graduate and Software Engineer interested in backend systems, optimization, intelligent applications, and software engineering.

* **GitHub:** `github.com/steph2502`
* **Portfolio:** `stephanie-s-portfolioo.vercel.app`
* **LinkedIn:** `linkedin.com/in/stephanieonwuagbaizu`

---

## License

Add the appropriate license for the repository if the project is intended to be reused or distributed.

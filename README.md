# SearchPlanning — Test Scheduling with Constraint Programming

Scheduling a test suite across machines and shared resources is a hard combinatorial problem. This project models it in **MiniZinc**, solves it with a CP solver, and uses a **conflict-graph heuristic** to estimate how good the solution is.

Built for the *Planeamento e Procura* course at Instituto Superior Técnico.

## The problem

Each test has:

- a **duration**
- a set of **machines** it can run on
- a set of **shared resources** it needs exclusively (a database, a licence, a device)

Tests that share a resource cannot overlap. Tests assigned to the same machine cannot overlap. The goal is to minimise the **makespan** — the time at which the last test finishes.

Input instances look like this:

```
% Number of machines: 10
% Number of resources: 3
test('t1', 4, ['m1','m2'], ['r1'])
test('t2', 7, ['m3'], ['r1','r2'])
...
```

## Two solvers, one model

**1. MiniZinc (`proj.mzn`).** The complete model: start times, machine assignment, no-overlap constraints for machine and resource conflicts, and a makespan variable bounded by a computed lower bound.

**2. Python heuristic (`proj.py`).** A greedy scheduler backed by a **conflict graph**: nodes are tests (weighted by duration), edges connect tests that share a resource. The heaviest clique in that graph is a provable lower bound on the makespan — no schedule can beat it. The same graph guides the order in which tests are placed.

The Python side also parses instances, calls the MiniZinc model through the `minizinc` Python API, writes the schedule, and reports the gap against the clique bound.

## Run

```bash
pip install minizinc networkx
python proj.py input.txt output.txt
```

Validate the result with the supplied checker:

```bash
python checker.py input.txt output.txt
# Solution is valid
```

## Output format

```
% Makespan : 42
machine('m1', 2, [('t3',0),('t7',12)])
machine('m2', 3, [('t1',0,['r1']),...])
```

`checker.py` re-parses this, verifies every test ran exactly once, and confirms there are no overlaps.

## Files

| File | Responsibility |
|---|---|
| `proj.mzn` | MiniZinc constraint model |
| `proj.py` | Instance parsing, clique bound, MiniZinc driver, output |
| `checker.py` | Independent solution validator |
| `tsp-instances/` | Benchmark instances |
| `input*.txt`, `output*.txt` | Small worked examples |
| `Project_S_P_2024_25.pdf` | Assignment statement |

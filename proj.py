import sys
import time
from minizinc import Instance, Model, Solver
import ast
from datetime import timedelta
import networkx as nx

# conflict graph creation and clique finding functions
def create_conflict_graph(test_cases):
    graph = nx.Graph()
    for idx1, test1 in enumerate(test_cases):
        name1, duration1, machines1, resources1 = test1
        graph.add_node(idx1, duration=duration1)
        for idx2, test2 in enumerate(test_cases):
            if idx1 < idx2:
                name2, duration2, machines2, resources2 = test2
                if set(resources1).intersection(resources2):
                    graph.add_edge(idx1, idx2)
    return graph

def get_max_weighted_clique(graph):
    # Heuristic approach to find the heaviest clique
    best_clique = []
    highest_weight = 0
    for clique in nx.find_cliques(graph):
        current_weight = sum(graph.nodes[node]['duration'] for node in clique)
        if current_weight > highest_weight:
            highest_weight = current_weight
            best_clique = clique
    return highest_weight, best_clique

# read and parse input
def read_input(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    total_tests = 0
    total_machines = 0
    total_resources = 0
    test_list = []

    for line in lines:
        line = line.strip()
        if line.startswith('%'):
            if 'Number of machines' in line:
                total_machines = int(line.split(':')[1].strip())
            elif 'Number of resources' in line:
                total_resources = int(line.split(':')[1].strip())
            continue
        if line.startswith('test('):
            content = line[line.find('(')+1 : line.rfind(')')]
            test_data = ast.literal_eval(f"({content})")
            test_name, duration, machines, resources = test_data
            test_list.append((test_name, duration, machines, resources))
            total_tests += 1

    return total_tests, total_machines, total_resources, test_list

def output_results(file_path, makespan, machine_details):
    with open(file_path, 'w') as f:
        f.write(f"% Makespan :  {makespan}\n")
        # Order machines numerically
        for machine, info in sorted(machine_details.items(), key=lambda x: int(x[0][1:])):
            task_count = len(info['tasks'])
            machine_line = f"machine( '{machine}', {task_count}, ["
            # Order tasks by their start times
            sorted_tasks = sorted(info['tasks'], key=lambda task: task[1])
            task_entries = []
            for task_name, start_time, resources in sorted_tasks:
                if resources:
                    res_str = '[' + ','.join(f"'{res}'" for res in resources) + ']'
                    task_entries.append(f"('{task_name}',{start_time},{res_str})")
                else:
                    task_entries.append(f"('{task_name}',{start_time})")
            machine_line += ','.join(task_entries) + "])\n"
            f.write(machine_line)

#Lower bound estimation
def estimate_optimal_makespan(num_machines, num_resources, test_cases):
    resource_times = {f"r{i+1}": 0 for i in range(num_resources)}
    machine_times = {f"m{i+1}": 0 for i in range(num_machines)}
    total_time = 0
    longest_test = 0

    for test in test_cases:
        name, duration, machines, resources = test
        total_time += duration
        longest_test = max(longest_test, duration)

        # Accumulate resource usage
        for res in resources:
            resource_times[res] += duration

        # Accumulate machine usage
        if machines:
            for mach in machines:
                machine_times[mach] += duration / len(machines)
        else:
            for mach in machine_times:
                machine_times[mach] += duration / num_machines

    max_resource = max(resource_times.values(), default=0)
    max_machine = max(machine_times.values(), default=0)
    avg_workload = total_time / num_machines

    # Create conflict graph and identify the heaviest clique
    conflict_graph = create_conflict_graph(test_cases)
    clique_weight, _ = get_max_weighted_clique(conflict_graph)

    optimal_estimate = max(
        max_resource,
        max_machine,
        longest_test,
        avg_workload,
        clique_weight
    )

    return optimal_estimate

def assign_schedule(test_indices, num_machines, num_resources, test_cases, output_file, start_timer):
    required_machines = []
    required_resources = []
    for idx in test_indices:
        machines = test_cases[idx][2]
        resources = test_cases[idx][3]
        machines_set = set(int(m.replace('m', '')) for m in machines) if machines else set(range(1, num_machines + 1))
        required_machines.append(machines_set)
        resources_set = set(int(r.replace('r', '')) for r in resources) if resources else set()
        required_resources.append(resources_set)

    resource_map = {}
    for pos, idx in enumerate(test_indices):
        for res in required_resources[pos]:
            resource_map.setdefault(res, set()).add(idx)

    restriction_scores = []
    for pos, idx in enumerate(test_indices):
        test = test_cases[idx]
        _, _, machines, resources = test
        avail_machines = len(required_machines[pos])
        req_resources = len(required_resources[pos])

        conflicts = set()
        for res in required_resources[pos]:
            conflicts.update(resource_map[res])
        conflicts.discard(idx)
        num_conflicts = len(conflicts)

        score = (num_machines - avail_machines) + req_resources + num_conflicts
        restriction_scores.append((idx, score))

    # Sort tests by restriction score descending
    restriction_scores.sort(key=lambda x: -x[1])
    sorted_indices = [idx for idx, _ in restriction_scores]

    # Estimate makespan
    relevant_tests = [test_cases[idx] for idx in sorted_indices]
    makespan_est = int(estimate_optimal_makespan(num_machines, num_resources, relevant_tests))

    min_mk = makespan_est
    max_mk = makespan_est + 10

    # Initialize MiniZinc model and solver
    model = Model("proj.mzn")
    solver = Solver.lookup("chuffed")
    instance = Instance(solver, model)

    durations = [test_cases[idx][1] for idx in sorted_indices]
    req_machines = [
        set(int(m.replace('m', '')) for m in test_cases[idx][2]) if test_cases[idx][2] else set(range(1, num_machines + 1))
        for idx in sorted_indices
    ]
    req_resources = [
        set(int(r.replace('r', '')) for r in test_cases[idx][3]) if test_cases[idx][3] else set()
        for idx in sorted_indices
    ]

    instance["n_tests"] = len(sorted_indices)
    instance["n_machines"] = num_machines
    instance["n_resources"] = num_resources
    instance["durations"] = durations
    instance["required_machines"] = req_machines
    instance["required_resources"] = req_resources
    instance["min_makespan"] = min_mk
    instance["max_makespan"] = max_mk

    # Solve with timeout and parallel processing
    solution = instance.solve(timeout=timedelta(minutes=4.5), processes=4)

    if solution.status.has_solution():
        final_makespan = solution["makespan"]
        start_times = solution["start_times"]
        machine_assignment = solution["assigned_machine"]

        machines_info = {f"m{i}": {'total_duration': 0, 'tasks': []} for i in range(1, num_machines + 1)}
        index_to_name = {idx: test_cases[idx][0] for idx in sorted_indices}

        for res_idx, test_idx in enumerate(sorted_indices):
            assigned_mach = machine_assignment[res_idx]
            machine = f"m{assigned_mach}"
            task_name = index_to_name[test_idx]
            start_time = start_times[res_idx]
            duration = durations[res_idx]
            resources = test_cases[test_idx][3] or []
            end_time = start_time + duration
            machines_info[machine]['tasks'].append((task_name, start_time, resources))
            machines_info[machine]['total_duration'] = max(machines_info[machine]['total_duration'], end_time)

        output_results(output_file, final_makespan, machines_info)
        elapsed = time.time() - start_timer
        #Execution time
        # with open(output_file, 'a') as f:
        #     f.write(f"% Execution Time: {elapsed:.2f} seconds\n")
    else:
        print("No feasible solution found for the provided tests.")
        with open(output_file, 'w') as f:
            f.write("% No feasible solution found for the provided tests.\n")
        elapsed = time.time() - start_timer
        with open(output_file, 'a') as f:
            f.write(f"% Execution Time: {elapsed:.2f} seconds\n")

def main(input_path, output_path):
    start_time = time.time()

    num_tests, num_machines, num_resources, tests = read_input(input_path)
    test_indices = range(num_tests)
    assign_schedule(test_indices, num_machines, num_resources, tests, output_path, start_time)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python proj.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    main(input_file, output_file)

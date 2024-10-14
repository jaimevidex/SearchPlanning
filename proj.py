import os
import sys
import time
from minizinc import Instance, Model, Solver
import ast
from datetime import timedelta

def parse_input(input_file):
    # Open and read the input file
    with open(input_file, 'r') as file:
        lines = file.readlines()

    # Initialize variables for the problem
    n_tests = 0
    n_machines = 0
    n_resources = 0
    tests = []

    for line in lines:
        line = line.strip()
        if line.startswith('%'):
            if 'Number of machines' in line:
                n_machines = int(line.split(':')[1].strip())  # Extract number of machines
            elif 'Number of resources' in line:
                n_resources = int(line.split(':')[1].strip())  # Extract number of resources
            continue
        if line.startswith('test('):
            # Extract the content inside the parentheses
            test_content = line[line.find('(')+1 : line.rfind(')')]
            # Safely evaluate the content
            test_data = ast.literal_eval(f"({test_content})")
            test_name = test_data[0]
            duration = test_data[1]
            machines = test_data[2]
            resources = test_data[3]
            tests.append((test_name, duration, machines, resources))
            n_tests += 1

    return n_tests, n_machines, n_resources, tests

def write_output(output_file, makespan, machine_assignments):
    with open(output_file, 'w') as file:
        file.write(f"% Makespan :  {makespan}\n")
        # Sort machines numerically
        for machine, details in sorted(machine_assignments.items(), key=lambda x: int(x[0][1:])):
            machine_output = f"machine( '{machine}', {details['total_duration']}, ["
            # Sort tasks by start_time
            tasks_sorted = sorted(details['tasks'], key=lambda x: x[1])  # x[1] is start_time
            task_strings = []
            for task_name, start_time, resources in tasks_sorted:
                if resources:
                    resources_str = '[' + ','.join(f"'{r}'" for r in resources) + ']'
                    task_strings.append(f"('{task_name}',{start_time},{resources_str})")
                else:
                    task_strings.append(f"('{task_name}',{start_time})")
            machine_output += ','.join(task_strings) + "])\n"
            file.write(machine_output)

def compute_optimal_makespan(n_tests, n_machines, n_resources, tests):
    # Initialize total durations
    resource_durations = {f"r{i+1}": 0 for i in range(n_resources)}
    machine_durations = {f"m{i+1}": 0 for i in range(n_machines)}
    total_duration = 0
    max_test_duration = 0

    for test in tests:
        test_name, duration, machines, resources = test
        total_duration += duration
        max_test_duration = max(max_test_duration, duration)

        # Update resource durations
        for r in resources:
            resource_durations[r] += duration

        # Update machine durations
        if machines:
            for m in machines:
                machine_durations[m] += duration

    # Compute maximal total durations
    max_resource_duration = max(resource_durations.values(), default=0)
    max_machine_duration = max(machine_durations.values(), default=0)
    workload_per_machine = total_duration / n_machines

    # Estimate optimal makespan
    optimal_makespan_estimate = max(
        max_resource_duration,
        max_machine_duration,
        max_test_duration,
        workload_per_machine
    )

    return optimal_makespan_estimate

def main(input_file, output_file):
    start_time = time.time()  # Record the start time

    # Parse the input file
    n_tests, n_machines, n_resources, tests = parse_input(input_file)

    # Compute minimal makespan estimate
    optimal_makespan_estimate = int(compute_optimal_makespan(n_tests, n_machines, n_resources, tests))
    print(f"\nEstimated optimal makespan: {optimal_makespan_estimate}")

    # Set min_makespan and max_makespan to the estimated minimal makespan
    min_makespan = optimal_makespan_estimate
    max_makespan = optimal_makespan_estimate
    print(f"Setting makespan to: {optimal_makespan_estimate}")

    # Define the MiniZinc model and solver
    proj_model = Model("proj.mzn")  # Ensure proj.mzn is in the same directory
    chuffed = Solver.lookup("chuffed")  # Use Chuffed solver

    # Create an instance of the model
    instance = Instance(chuffed, proj_model)

    # Prepare the input data for the model
    durations = [test[1] for test in tests]
    required_machines = [set([int(m.strip('m')) for m in test[2]]) if test[2] else set(range(1, n_machines + 1)) for test in tests]
    required_resources = [set([int(r.strip('r')) for r in test[3]]) if test[3] else set() for test in tests]

    # Assign data to MiniZinc instance
    instance["n_tests"] = n_tests
    instance["n_machines"] = n_machines
    instance["n_resources"] = n_resources
    instance["durations"] = durations
    instance["required_machines"] = required_machines
    instance["required_resources"] = required_resources
    instance["min_makespan"] = min_makespan
    instance["max_makespan"] = max_makespan
    instance["MODE"] = 0  # Set to satisfaction mode

    # Solve the instance with a time limit and multiple processes
    result = instance.solve(timeout=timedelta(minutes=5), processes=4)

    # Check if the model found a feasible solution
    if result.status.has_solution():
        # Retrieve results from the solution
        makespan = result["makespan"]
        start_times = result["start_times"]
        assigned_machine = result["assigned_machine"]

        # Initialize machine_assignments with all machines
        machine_assignments = {f"m{i}": {'total_duration': 0, 'tasks': []} for i in range(1, n_machines + 1)}

        # Process machine assignments and group tasks by machine
        for i in range(n_tests):
            machine_idx = assigned_machine[i]  # Assigned machine index (1-based)
            machine = f"m{machine_idx}"
            # No need to check if machine exists, since we've initialized all of them
            task_name = tests[i][0]  # Test name
            start_time_task = start_times[i]
            duration = durations[i]
            resources = [f"r{r}" for r in required_resources[i]] if required_resources[i] else []
            machine_assignments[machine]['tasks'].append((task_name, start_time_task, resources))
            machine_assignments[machine]['total_duration'] += duration

        # Write the output to the file
        write_output(output_file, makespan, machine_assignments)
    else:
        # Handle the case where no solution was found
        print("No feasible solution found.")
        with open(output_file, 'w') as file:
            file.write("% No feasible solution found.\n")

    elapsed_time = time.time() - start_time  # Calculate elapsed time

    # Append the execution time to the output file
    with open(output_file, 'a') as file:
        file.write(f"% Execution Time: {elapsed_time:.2f} seconds\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python proj.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Run the main function
    main(input_file, output_file)
import minizinc
import sys
import re
import time

# Function to parse and convert the test data from .txt file
def parse_test_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Extract number of tests, machines, resources
    test_info = {
        'T': 0,
        'M': 0,
        'R': 0,
        'tests': []
    }

    allMachines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('%'):
            if 'Number of tests' in line:
                test_info['T'] = int(re.search(r': (\d+)', line).group(1))
            elif 'Number of machines' in line:
                test_info['M'] = int(re.search(r': (\d+)', line).group(1))
                for i in range(0,test_info['M'] ):
                    allMachines.append("m"+str(i+1))
            elif 'Number of resources' in line:
                test_info['R'] = int(re.search(r': (\d+)', line).group(1))
        elif line.startswith('test'):
            # Parse each test
            test_match = re.search(r"test\(\s*'(\w+)'\s*,\s*(\d+)\s*,\s*\[(.*?)\]\s*,\s*\[(.*?)\]\s*\)", line)
            name = test_match.group(1)
            duration = int(test_match.group(2))
            
            # Extract machines and resources
            raw_machines = test_match.group(3)
            raw_resources = test_match.group(4)
            
            # Normalize quotes and split the values
            machines = [m.strip().strip("'") for m in raw_machines.split(',') if m.strip()]
            resources = [r.strip().strip("'") for r in raw_resources.split(',') if r.strip()]
            
            # Check if machines list is empty, and use all available machines if so
            if not machines:
                machines = allMachines  # Use the global variable
            
            test_info['tests'].append((name, duration, machines, resources))
                    
    return test_info

# Convert parsed data to MiniZinc format
def convert_to_mzn_format(test_info):
    durations = []
    allowed_machines = []
    required_resources = []
    
    # Convert tests
    for test in test_info['tests']:
        name, duration, machines, resources = test
        
        # Append duration
        durations.append(duration)
        
        # If machines list is empty, allow any machine
        if not machines:
            allowed_machines.append(set(range(1, test_info['M'] + 1)))
        else:
            allowed_machines.append(set(int(m[1]) for m in machines))
        
        # If resources list is empty, add an empty set
        if not resources:
            required_resources.append(set())
        else:
            required_resources.append(set(int(r[1]) for r in resources))
    
    return durations, allowed_machines, required_resources

# Load data from .txt file and prepare for MiniZinc
def load_test_data(filename):
    test_info = parse_test_file(filename)
    durations, allowed_machines, required_resources = convert_to_mzn_format(test_info)
    return test_info['T'], test_info['M'], test_info['R'], durations, allowed_machines, required_resources

def process_schedule(result, T, test_info):
    machine_schedule = {}
    
    # Create a dictionary to map test IDs to their resource usage
    test_resources = {test[0]: test[3] for test in test_info['tests']}  # Assuming test_info['tests'] has (name, duration, machines, resources)
    
    # Collect task details for each machine
    task_details = []
    for i in range(1, T + 1):
        m = result["machine"][i - 1]  # Machine to which the test is assigned
        start_time = result["start"][i - 1]  # Start time of the test
        test_id = f't{i}'  # Test identifier
        resources = test_resources.get(test_id, [])  # Resources required for the test
        
        # Format the task details with optional resources
        task_detail = (f"'{test_id}'", start_time,)  # Start with test_id and start_time as a tuple
        if resources:
            resources = list(resources)  # Convert the set to a list to access elements
            # If there are resources, add them as part of the tuple
            task_detail = (f"'{test_id}'", start_time, [f"r{r}" for r in resources])
        
        # Collect task details to be sorted later
        task_details.append((m, task_detail))

    # Group tasks by machine and sort by start time for each machine
    for m, task_detail in task_details:
        if m not in machine_schedule:
            machine_schedule[m] = []
        machine_schedule[m].append(task_detail)
    
    # Sort tasks by start time for each machine
    for m in machine_schedule:
        machine_schedule[m].sort(key=lambda x: x[1])  # Sort by the second element (start_time)
    
    # Format the task details into strings for each machine
    for m in machine_schedule:
        machine_schedule[m] = [f"({', '.join(map(str, task))})" for task in machine_schedule[m]]
    
    return machine_schedule

def output_results(filename, result, test_info, machines_schedule):
    with open(filename, 'w') as file:
        # Write makespan
        file.write(f"% Makespan : {result['makespan']}\n")
        # Write machine schedules
        for m in range(1, test_info['M'] + 1):
            machine_tasks = machines_schedule.get(m, [])
            tasks_str = ','.join(machine_tasks)
            file.write(f"machine( 'm{m}', {len(machine_tasks)}, [{tasks_str}])\n")


# Main execution
if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    # if no more arguments are provided, the default value is 0
    nrThreads = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    # Load the data from the input file
    T, M, R, durations, allowed_machines, required_resources = load_test_data(input_file)
    
    # Create a MiniZinc model
    model = minizinc.Model()
    model.add_file("./Project.mzn")
    
    # Find the MiniZinc solver configuration for Gecode
    solver = minizinc.Solver.lookup("chuffed")
    instance = minizinc.Instance(solver, model)

    # Assign parameters
    instance["T"] = T
    instance["M"] = M
    instance["R"] = R
    instance["duration"] = durations
    instance["allowed_machines"] = allowed_machines
    instance["required_resources"] = required_resources
    
    # Set the number of threads
    if nrThreads != 0 :
        instance["threads"] = nrThreads # Adjust the number of threads as needed 


    # Record the start time
    start_time = time.time()
    # Solve asynchronously
    result = instance.solve()
    # Record the end time
    end_time = time.time()

    # Calculate the elapsed time
    elapsed_time = end_time - start_time

    # Process the result to map tasks to machines
    machine_schedule = process_schedule(result, T, {
        'tests': [(f't{i+1}', duration, machines, resources) for i, (duration, machines, resources) in enumerate(zip(durations, allowed_machines, required_resources))]
    })
    
        # Output the result to the output file
    output_results(output_file, result, {"T": T, "M": M, "R": R}, machine_schedule)

    # Output the elapsed time to the output file
    with open(output_file, 'a') as f:
        f.write(f"\nElapsed time: {elapsed_time:.2f} seconds\n")
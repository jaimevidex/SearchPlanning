import minizinc
import sys
import re

# Function to parse and convert the test data from .txt file
def parse_test_file(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Extract number of tests, machines, resources, and max makespan
    test_info = {
        'T': 0,
        'M': 0,
        'R': 0,
        'max_makespan': 0,
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
            elif 'Maximum makespan' in line:
                test_info['max_makespan'] = int(re.search(r': (\d+)', line).group(1))
        elif line.startswith('test'):
            # Parse each test
            test_match = re.search(r"test\(\s*’(\w+)’\s*,\s*(\d+)\s*,\s*\[(.*?)\]\s*,\s*\[(.*?)\]\s*\)", line)
            name = test_match.group(1)
            duration = int(test_match.group(2))
            
            # Extract machines and resources
            raw_machines = test_match.group(3)
            raw_resources = test_match.group(4)
            
            # Normalize quotes and split the values
            machines = [m.strip().strip("’") for m in raw_machines.split(',') if m.strip()]
            resources = [r.strip().strip("’") for r in raw_resources.split(',') if r.strip()]
            
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
    return test_info['T'], test_info['M'], test_info['R'], test_info['max_makespan'], durations, allowed_machines, required_resources

def process_schedule(result, T, test_info):
    machine_schedule = {}
    
    # Create a dictionary to map test IDs to their resource usage
    test_resources = {test[0]: test[3] for test in test_info['tests']}  # Assuming test_info['tests'] has (name, duration, machines, resources)
    
    for i in range(1, T + 1):
        m = result["machine"][i - 1]
        start_time = result["start"][i - 1]
        test_id = f't{i}'
        resources = test_resources.get(test_id, [])
        
        # Format the task details with optional resources
        task_detail = f"(’{test_id}’, {start_time}"
        if resources:
            # Format resources as a comma-separated list if there are multiple resources
            resources_str = ', '.join(f"’r{r}’" for r in resources)
            task_detail += f", {resources_str}"
        task_detail += ")"
        
        if m not in machine_schedule:
            machine_schedule[m] = []
        machine_schedule[m].append(task_detail)
    
    return machine_schedule


def output_results(filename, result, test_info, machines_schedule):
    with open(filename, 'w') as file:
        # Write makespan
        file.write(f"% Makespan : {result['makespan']}\n")
        # Write machine schedules
        for m in range(1, test_info['M'] + 1):
            machine_tasks = machines_schedule.get(m, [])
            tasks_str = ','.join(machine_tasks)
            file.write(f"machine( ’m{m}’, {len(machine_tasks)}, [{tasks_str}])\n")


# Main execution
if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Load the data from the input file
    T, M, R, max_makespan, durations, allowed_machines, required_resources = load_test_data(input_file)
    
    # Create a MiniZinc model
    model = minizinc.Model()
    model.add_file("./Project.mzn")
    
    # Find the MiniZinc solver configuration for Gecode
    gecode = minizinc.Solver.lookup("gecode")
    instance = minizinc.Instance(gecode, model)

    # Assign parameters
    instance["T"] = T
    instance["M"] = M
    instance["R"] = R
    instance["MaxMakespan"] = max_makespan
    instance["duration"] = durations
    instance["allowed_machines"] = allowed_machines
    instance["required_resources"] = required_resources
    
    # Solve asynchronously
    result = instance.solve()

    # Process the result to map tasks to machines
    machine_schedule = process_schedule(result, T, {
        'tests': [(f't{i+1}', duration, machines, resources) for i, (duration, machines, resources) in enumerate(zip(durations, allowed_machines, required_resources))]
    })
    
    # Output the result to the output file
    output_results(output_file, result, {"T": T, "M": M, "R": R}, machine_schedule)


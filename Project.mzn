% Project PP

% Parameters
int: T;  % Number of tests
int: M;  % Number of machines
int: R;  % Number of resources
int: MaxMakespan;  % Maximum allowed makespan

array[1..T] of int: duration;  % Duration of each test
array[1..T] of set of int: allowed_machines;  % Machines each test can be run on
array[1..T] of set of int: required_resources;  % Resources each test requires

% Decision Variables
array[1..T] of var 0..sum(duration): start;  % Start time for each test
array[1..T] of var 1..sum(duration): end;    % End time for each test
array[1..T] of var 1..M: machine;  % Machine assignment for each test

var int: makespan;  % Overall time to finish all tests

% Constraints

% Ensure end times are calculated correctly
constraint forall(i in 1..T)(
    end[i] = start[i] + duration[i]
);

% Ensure tests assigned to the same machine do not overlap
constraint forall(i, j in 1..T where i != j)(
    if machine[i] = machine[j] then
        end[i] <= start[j] \/ end[j] <= start[i]
    else
        true
    endif
);

% Ensure tests requiring the same resource do not overlap
constraint forall(i, j in 1..T where i != j)(
    forall(r in required_resources[i] intersect required_resources[j]) (
        end[i] <= start[j] \/ end[j] <= start[i]
    )
);

% Machine assignment is restricted to allowed machines
constraint forall(i in 1..T)(
    machine[i] in allowed_machines[i]
);

% Objective: Minimize the makespan
constraint makespan = max([end[i] | i in 1..T]);

% Add the constraint for the maximum makespan
constraint makespan <= MaxMakespan;

solve minimize makespan;

output [
    "makespan = \(makespan)\n",
    "start = \(start)\n",
    "end = \(end)\n",
    "machine = \(machine)\n",
    "required_resources = \(required_resources)\n"
];

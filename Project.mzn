% Project PP

% Parameters
int: T;  % Number of tests
int: M;  % Number of machines
int: R;  % Number of resources

array[1..T] of int: duration;  % Duration of each test
array[1..T] of set of 1..M: allowed_machines;  % Machines each test can be run on
array[1..T] of set of 1..R: required_resources;  % Resources each test requires

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
    machine[i] = machine[j] -> (start[i] >= end[j] \/ start[j] >= end[i])
);

% Ensure tests requiring the same resource do not overlap
constraint forall(i, j in 1..T where i != j)(
    (required_resources[i] intersect required_resources[j] != {}) ->
        (start[i] >= end[j] \/ start[j] >= end[i])
);


% Machine assignment is restricted to allowed machines
constraint forall(i in 1..T)(
    machine[i] in allowed_machines[i]
);

% Objective: Minimize the makespan
constraint makespan = max(end);

solve minimize makespan;

output [
    "makespan = \(makespan)\n",
    "start = \(start)\n",
    "end = \(end)\n",
    "machine = \(machine)\n",
    "required_resources = \(required_resources)\n"
];
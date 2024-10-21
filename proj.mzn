int: n_tests;
int: n_machines;
int: n_resources;
int: max_makespan;
int: min_makespan;

array[1..n_tests] of int: durations;
array[1..n_tests] of set of int: required_machines;
array[1..n_tests] of set of int: required_resources;

int: max_time = sum(durations);

% Decision variables
array[1..n_tests] of var 0..max_time: start_times;
array[1..n_tests] of var 1..n_machines: assigned_machine;
var min_makespan..max_makespan: makespan;

% No overlap on the same machine
constraint
    forall(i, j in 1..n_tests where i < j)(
        assigned_machine[i] = assigned_machine[j] ->
        (start_times[i] >= start_times[j] + durations[j] \/ start_times[j] >= start_times[i] + durations[i])
    );

% No overlap if resources conflict
constraint
    forall(i, j in 1..n_tests where i < j)(
        card(required_resources[i] intersect required_resources[j]) > 0 ->
        (start_times[i] >= start_times[j] + durations[j] \/ start_times[j] >= start_times[i] + durations[i])
    );

% Enforce machine requirements
constraint
    forall(i in 1..n_tests)(
        assigned_machine[i] in required_machines[i]
    );

% Makespan definition
constraint
    forall(i in 1..n_tests)(
        makespan >= start_times[i] + durations[i]
    );

% Objective
solve minimize makespan;

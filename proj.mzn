int: n_tests;
int: n_machines;
int: n_resources;
int: max_makespan;
int: min_makespan;
int: MODE; % 1 for minimize makespan, 0 for fixed makespan

array[1..n_tests] of int: durations;
array[1..n_tests] of set of int: required_machines;
array[1..n_tests] of set of int: required_resources;

int: max_time = sum(durations);

% Decision variables
array[1..n_tests] of var 0..max_time: start_times;
array[1..n_tests] of var 0..max_time: end_times;
array[1..n_tests] of var 1..n_machines: assigned_machine;
var 0..max_time: makespan;
var 0..max_time: objective;

% Constraints
constraint
    forall(i in 1..n_tests) (
        end_times[i] = start_times[i] + durations[i]
    );

% No overlap on the same machine
constraint
    forall(i, j in 1..n_tests where i < j)(
        assigned_machine[i] = assigned_machine[j] ->
        (start_times[i] >= end_times[j] \/ start_times[j] >= end_times[i])
    );

% No overlap if resources conflict
constraint
    forall(i, j in 1..n_tests where i < j)(
        card(required_resources[i] intersect required_resources[j]) > 0 ->
        (start_times[i] >= end_times[j] \/ start_times[j] >= end_times[i])
    );

% Enforce machine requirements
constraint
    forall(i in 1..n_tests)(
        (card(required_machines[i]) > 0) ->
        assigned_machine[i] in required_machines[i]
    );

% Makespan definition
constraint
    forall(i in 1..n_tests)(
        makespan >= end_times[i]
    );

constraint makespan <= max_makespan;
constraint makespan >= min_makespan;

% Enforce makespan to be min_makespan when in satisfaction mode
constraint
    (MODE = 0) -> (makespan = min_makespan);

% Objective definition
constraint
    objective = if MODE = 1 then makespan else 0 endif;

% Objective
solve minimize objective;
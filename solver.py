import dataclasses
import math
import os
import sys

import cplex
import typing as t


@dataclasses.dataclass
class SolverSuccess:
    a_matrix: t.List[t.List[int]]
    c_vector: t.List[int]
    n_vector: t.List[int]
    total_cost: int


@dataclasses.dataclass
class SolverError:
    a_matrix: t.List[t.List[int]]
    c_vector: t.List[int]
    error: str


def generate_partition_with_lengths(l: int, lengths: t.List[int]) -> t.List[int]:
    if len(lengths) == 0:
        return [l]

    head, tail = lengths[0], lengths[1:]

    res = [head for _ in range(0, l // head)]
    res += generate_partition_with_lengths(l % head, tail)
    return res


def generate_partitions(l: int, l1: int, l2: int, l3: int):
    first_optimal_partition = generate_partition_with_lengths(l, [l1, l2, l3])
    optimal_partitions = [first_optimal_partition]

    last_partition_is_the_final_one = False
    while True:
        last_partition = optimal_partitions[-1]

        modification_starting_position = len(last_partition) - 2
        while last_partition[modification_starting_position] == l3:
            modification_starting_position -= 1
            if modification_starting_position == -1:
                last_partition_is_the_final_one = True
                break

        if last_partition_is_the_final_one:
            break

        new_partition = last_partition[:modification_starting_position]

        modification_starting_value = {
            l1: l2,
            l2: l3
        }[last_partition[modification_starting_position]]

        new_partition.append(modification_starting_value)

        length_to_continue = {
            l2: [l2, l3],
            l3: [l3]
        }[modification_starting_value]

        new_partition += generate_partition_with_lengths(
            l - sum(new_partition),
            length_to_continue
        )

        optimal_partitions.append(new_partition)

    return optimal_partitions


def cplex_solver(
    base_matrix: t.List[t.List[int]], c_vector: t.List[int], m1: int, m2: int, m3: int, n_bound: int
) -> t.Union[SolverSuccess, SolverError]:
    problem = cplex.Cplex()
    problem.objective.set_sense(problem.objective.sense.minimize)

    # the matrix input to the IP solver:
    a_matrix = [
        [m2*base_matrix[0][j] - m1*base_matrix[1][j] for j in range(len(c_vector))],
        [m1*base_matrix[1][j] - m2*base_matrix[0][j] for j in range(len(c_vector))],
        [m3*base_matrix[1][j] - m2*base_matrix[2][j] for j in range(len(c_vector))],
        [m2*base_matrix[2][j] - m3*base_matrix[1][j] for j in range(len(c_vector))],
        [1 for _ in range(len(c_vector))],
        [1 for _ in range(len(c_vector))]
    ]

    try:
        column_names = ["n" + str(i) for i in range(len(c_vector))]
        problem.variables.add(
            obj=c_vector,
            lb=[0.0 for _ in range(len(c_vector))],
            ub=[cplex.infinity for _ in range(len(c_vector))],
            types="".join(["I" for _ in range(len(c_vector))]),
            names=column_names
        )

        problem.linear_constraints.add(
            lin_expr=[(column_names, row) for row in a_matrix],
            senses="LLLLLG",
            rhs=[0.0, 0.0, 0.0, 0.0, n_bound, 1.0]
        )

        problem.solve()
    except cplex.CplexError as exc:
        return SolverError(
            a_matrix=a_matrix, c_vector=c_vector, error=str(exc)
        )

    return SolverSuccess(
        a_matrix=a_matrix,
        c_vector=c_vector,
        n_vector=list(problem.solution.get_values()),
        total_cost=problem.solution.get_objective_value()
    )


def solver(
    l: int, l1: int, l2: int, l3: int, m1: int, m2: int, m3: int, n_bound: int
):
    # we first generate the list of all optimal partitions [p_1, ..., p_k]
    # from lengths l1 > l2 > l3 and total length l
    partitions = generate_partitions(l, l1, l2, l3)

    # the matrix that codifies the partition quantities:
    # base_matrix[i][j] = N_i(p_j) is the multiplicity of length li in p_j
    base_matrix = [
        [len([() for v in p if v == length]) for p in partitions]
        for length in [l1, l2, l3]
    ]

    # the vector that codifies the clipping piece of each partition
    c_vector = [p[-1] for p in partitions]

    print("----------------------------------------------------------------------")
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    result = cplex_solver(base_matrix, c_vector, m1, m2, m3, n_bound)
    sys.stdout = old_stdout

    if isinstance(result, SolverError):
        print(f"An error was found when running cplex solver:\n> {str(result.error)}")
        print("----------------------------------------------------------------------")
        return

    # We display the results
    indexed_result_multiplicities = list(zip(range(0, len(partitions)), result.n_vector))
    result_multiplicities = [n for n in result.n_vector if n != 0]
    result_rows = [i for (i, n) in indexed_result_multiplicities if n != 0]
    quantities_returned = {l1: 0, l2: 0, l3: 0}
    total_cost_returned = 0
    for i in range(len(result_rows)):
        total_cost_returned += int(result_multiplicities[i]*c_vector[result_rows[i]])
        quantities_returned[l1] += int(result_multiplicities[i]*base_matrix[0][result_rows[i]])
        quantities_returned[l2] += int(result_multiplicities[i]*base_matrix[1][result_rows[i]])
        quantities_returned[l3] += int(result_multiplicities[i]*base_matrix[2][result_rows[i]])
    print()

    repeating_factor = m1 / math.gcd(m1, quantities_returned[l1])
    quantities = {
        k: quantities_returned[k]*repeating_factor for k in quantities_returned.keys()
    }

    for i in range(len(result_rows)):
        print("Partition " + str(partitions[result_rows[i]]) + " x " + str(int(result_multiplicities[i]*repeating_factor)))
        print(
            "Quantities for length:  " +
            f"{str(l1)}: {str(base_matrix[0][result_rows[i]]*int(result_multiplicities[i]*repeating_factor))}"
            f", {str(l2)}: {str(base_matrix[1][result_rows[i]]*int(result_multiplicities[i]*repeating_factor))}"
            f", {str(l3)}: {str(base_matrix[2][result_rows[i]]*int(result_multiplicities[i]*repeating_factor))}"
        )

    batch_size = int(quantities[l1]/m1)

    print()
    print()
    print("Check solution adequacy:")
    print(
        f"Length {l1} total quantity: {str(quantities[l1])}\n"
        f"Length {l2} total quantity: {str(quantities[l2])}\n"
        f"Length {l3} total quantity: {str(quantities[l3])}\n"
    )
    assert batch_size*m1 == quantities[l1]
    assert batch_size*m2 == quantities[l2]
    assert batch_size*m3 == quantities[l3]

    total_rods = sum(result_multiplicities)*repeating_factor
    total_cost = total_cost_returned*repeating_factor

    print()
    print(f"Total rods of length l needed : {total_rods}")
    print(f"Batch size : {batch_size}")
    print(f"Total cost: {total_cost}")
    print("----------------------------------------------------------------------")


if __name__ == '__main__':
    try:
        l, l1, l2, l3, m1, m2, m3, n_bound = [int(val) for val in sys.argv[1:]]
        
        if not ((l > l1) and (l1 > l2) and (l2 > l3) and l3 > 0):
            raise ValueError("Basic order and positivity conditions are not satisfied")
        if not (m1 > 0 and m2 > 0 and m3 > 0):
            raise ValueError("Basic order and positivity conditions are not satisfied")

    except Exception as _e:
        print(
            "Usage: python3 solver.py l l1 l2 l3 m1 m2 m3 n_bound,\n"
            "where l is the total length, l1 > l2 > l3 are the partition length,\n"
            "m1, m2 and m3 are the respective manufacturing multiplicities\n"
            "and n_bound is the greatest value admitted for the batch size\n"
        )
    else:
        solver(l, l1, l2, l3, m1, m2, m3, n_bound)

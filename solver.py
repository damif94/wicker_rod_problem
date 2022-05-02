import dataclasses
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
    base_matrix: t.List[t.List[int]], c_vector: t.List[int], n_bound: int
) -> t.Union[SolverSuccess, SolverError]:
    problem = cplex.Cplex()
    problem.objective.set_sense(problem.objective.sense.minimize)

    # the matrix input to the IP solver:
    a_matrix = [
        [base_matrix[0][j] - base_matrix[1][j] for j in range(len(c_vector))],
        [base_matrix[1][j] - base_matrix[0][j] for j in range(len(c_vector))],
        [base_matrix[1][j] - base_matrix[2][j] for j in range(len(c_vector))],
        [base_matrix[2][j] - base_matrix[1][j] for j in range(len(c_vector))],
        [1 for _ in range(len(c_vector))],
        [1 for _ in range(len(c_vector))]
    ]

    try:
        column_names = ["n" + str(i) for i in range(len(c_vector))]
        print(len(c_vector))
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


def solver(l: int, l1: int, l2: int, l3: int, n_bound: int):
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
    result = cplex_solver(base_matrix, c_vector, n_bound)
    sys.stdout = old_stdout

    if isinstance(result, SolverError):
        print(f"An error was found when running cplex solver:\n> {str(result.error)}")
        print("----------------------------------------------------------------------")
        return

    # We display the results
    indexed_result_multiplicities = list(zip(range(0, len(partitions)), result.n_vector))
    result_multiplicities = [n for n in result.n_vector if n != 0]
    result_rows = [i for (i, n) in indexed_result_multiplicities if n != 0]
    check = {l1: 0, l2: 0, l3: 0, 0: 0}
    for i in range(len(result_rows)):
        print("Partition " + str(partitions[result_rows[i]]) + " x " + str(int(result_multiplicities[i])))
        print(
            "Quantities for length:  " +
            f"{str(l1)}: {str(base_matrix[0][result_rows[i]])}"
            f", {str(l2)}: {str(base_matrix[1][result_rows[i]])}"
            f", {str(l3)}: {str(base_matrix[2][result_rows[i]])}"
        )
        check[0] += result_multiplicities[i]*c_vector[result_rows[i]]
        check[35] += result_multiplicities[i]*base_matrix[0][result_rows[i]]
        check[30] += result_multiplicities[i] * base_matrix[1][result_rows[i]]
        check[20] += result_multiplicities[i] * base_matrix[2][result_rows[i]]
    print()
    print()
    print("Check solution adequacy:")
    print(
        f"Length 35 total quantity: {str(check[35])}\n"
        f"Length 30 total quantity: {str(check[30])}\n"
        f"Length 20 total quantity: {str(check[20])}\n"
    )
    assert check[35] == check[30] == check[20]

    print()
    print(f"Total items of length l: {sum(result_multiplicities)}")
    print(f"Total cost: {str(check[0])}")
    print("----------------------------------------------------------------------")


if __name__ == '__main__':
    try:
        l, l1, l2, l3, n_bound = [int(val) for val in sys.argv[1:]]

        if (total := l1 + l2 + l3) > l:
            raise ValueError(f"Sum of lengths for pieces ({total}) is greater than l ({l})")

        if not ((l > l1) and (l1 > l2) and (l2 > l3) and l3 > 0):
            raise ValueError("Basic order and positivity conditions are not satisfied")

    except Exception as _e:
        print(
            "Usage: python3 solver.py l l1 l2 l3 n_bound\n"
            "where l is the total length and l1 > l2 > l3 are the partition lengths"
        )
    else:
        solver(l, l1, l2, l3, n_bound)

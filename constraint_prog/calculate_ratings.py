from ortools.sat.python import cp_model


class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, variables1, variables2):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables1 = variables1
        self.__variables2 = variables2
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        for v1, v2 in zip(self.__variables1, self.__variables2):
            print("(%i, %i)" % (self.Value(v1), self.Value(v2)), end=" ")
        print()

    def solution_count(self):
        return self.__solution_count


def SearchForAllSolutionsSampleSat(team_rating, n_unique_ratings, rating_range):
    """Showcases calling the solver to search for all solutions."""
    # Creates the model.
    model = cp_model.CpModel()

    # Creates the variables.
    TEAM_SIZE = 11
    if type(rating_range) == int:
        rating_range = (rating_range, rating_range)
    min_rating = max(team_rating - rating_range[0], 0)
    max_rating = min(team_rating + rating_range[1], 99)

    variable_ratings = {}
    variable_counts = {}
    variable_multiplied = {}
    variable_excess = {}
    variable_maxexcess = {}
    variable_maxexcessmultiplied = {}

    for unique_rating in range(n_unique_ratings):
        variable_ratings[unique_rating] = model.NewIntVar(
            min_rating, max_rating, "rating_{}".format(unique_rating)
        )
        variable_counts[unique_rating] = model.NewIntVar(
            1, TEAM_SIZE, "count_{}".format(unique_rating)
        )
        variable_multiplied[unique_rating] = model.NewIntVar(
            min_rating, max_rating * TEAM_SIZE, "multiplied_{}".format(unique_rating)
        )
        variable_excess[unique_rating] = model.NewIntVar(
            -max_rating * TEAM_SIZE,
            max_rating * TEAM_SIZE,
            "excess_{}".format(unique_rating),
        )
        variable_maxexcess[unique_rating] = model.NewIntVar(
            0, max_rating * TEAM_SIZE, "maxexcess_{}".format(unique_rating)
        )
        variable_maxexcessmultiplied[unique_rating] = model.NewIntVar(
            0,
            max_rating * TEAM_SIZE * TEAM_SIZE,
            "maxexcessmultiplied_{}".format(unique_rating),
        )

    variable_baserating = model.NewIntVar(
        min_rating * TEAM_SIZE, max_rating * TEAM_SIZE, "baserating"
    )
    variable_totalrating = model.NewIntVar(
        min_rating * TEAM_SIZE * TEAM_SIZE,
        max_rating * TEAM_SIZE * TEAM_SIZE,
        "totalrating",
    )
    variable_finalrating = model.NewIntVar(min_rating, max_rating, "finalrating")

    # Creates the constraints.

    # Set the number of players to TEAM_SIZE.
    model.Add(sum(variable_counts.values()) == TEAM_SIZE)

    # Make sure that the count decreases for each rating.
    for unique_rating in range(1, n_unique_ratings):
        model.Add(variable_counts[unique_rating] <= variable_counts[unique_rating - 1])

    # Make sure that no rating is repeated.
    model.AddAllDifferent(variable_ratings.values())

    # Make sure that when a count value occurs twice, the rating always decreases. This prevents permutation of the same solution.
    variable_bool = {}
    for unique_rating in range(1, n_unique_ratings):
        variable_bool[unique_rating] = model.NewBoolVar("bool_{}".format(unique_rating))
        model.Add(
            variable_counts[unique_rating] == variable_counts[unique_rating - 1]
        ).OnlyEnforceIf(variable_bool[unique_rating])
        model.Add(
            variable_counts[unique_rating] != variable_counts[unique_rating - 1]
        ).OnlyEnforceIf(variable_bool[unique_rating].Not())
        model.Add(
            variable_ratings[unique_rating] < variable_ratings[unique_rating - 1]
        ).OnlyEnforceIf(variable_bool[unique_rating])

    # Link the counts to the ratings.
    for rating_group in range(n_unique_ratings):
        model.AddMultiplicationEquality(
            variable_multiplied[rating_group],
            [variable_ratings[rating_group], variable_counts[rating_group]],
        )

    # Get the base rating.
    model.Add(variable_baserating == sum(variable_multiplied.values()))

    # Get the excess ratings.
    for unique_rating in range(n_unique_ratings):
        model.Add(
            variable_excess[unique_rating]
            == variable_ratings[unique_rating] * TEAM_SIZE - variable_baserating
        )
        model.AddMaxEquality(
            variable_maxexcess[unique_rating], [variable_excess[unique_rating], 0]
        )
        model.AddMultiplicationEquality(
            variable_maxexcessmultiplied[unique_rating],
            [variable_maxexcess[unique_rating], variable_counts[unique_rating]],
        )

    # Combine excess and base ratings.
    model.Add(
        variable_totalrating
        == variable_baserating * TEAM_SIZE + sum(variable_maxexcessmultiplied.values())
    )

    # Get the total rating.
    model.AddDivisionEquality(
        variable_finalrating, variable_totalrating, TEAM_SIZE * TEAM_SIZE
    )

    # Constrain the final rating to the team rating.
    model.Add(variable_finalrating == team_rating)

    # Create a solver and solve.
    solver = cp_model.CpSolver()
    solution_printer = VarArraySolutionPrinter(
        variable_counts.values(), variable_ratings.values()
    )
    # Enumerate all solutions.
    solver.parameters.enumerate_all_solutions = True
    # Solve.
    status = solver.Solve(model, solution_printer)

    print("Status = %s" % solver.StatusName(status))
    print("Number of solutions found: %i" % solution_printer.solution_count())


if __name__ == "__main__":
    SearchForAllSolutionsSampleSat(83, 3, [5, 2])

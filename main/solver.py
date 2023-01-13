from ortools.sat.python import cp_model
import json
from typing import List, Union
from utils.stats import team_rating


FORMATION_FILE = "../src/formations.json"


class SBCSolver:
    def __init__(
        self,
        data: List[List[Union[int, str, list]]],
        formation: str = "442",
        minimize: bool = False,
    ) -> None:

        self.data = data
        self.formation = formation
        self.minimize = minimize

        self.team_size = None
        self.formation_list = None

        self._variables_id = None
        self._constraints = None

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        self._get_formation_info()

    def _get_formation_info(self) -> None:

        with open(FORMATION_FILE) as f:
            data = json.load(f)
        self.formation_list = data[self.formation]
        self.team_size = len(self.formation_list)

    def build(self, constraints: dict = None) -> None:
        """Build CP-SAT model based on provided constraints.

        Args:
            constraints (dict, optional): A dictionary specifying all
                constraints. All possible key/value pairs are given
                below. Defaults to None.

        Key/Value Pairs:
            minimum_team_rating (int): Minimum team rating.
            max_cost (int): Maximum cost of the team.
        """

        if constraints is None:
            constraints = {}
        self._constraints = constraints

        self._build_base_constraint()

        if "minimum_team_rating" in constraints:
            self._build_rating_constraint(constraints["minimum_team_rating"])

        if "max_cost" in constraints:
            self._build_cost_constraint(constraints["max_cost"])
        else:
            self._build_minimization()

    def _build_base_constraint(self) -> None:

        # Variables
        self._variables_id = {}
        for ind, player_data in enumerate(self.data):
            self._variables_id[ind] = self.model.NewBoolVar(
                "id_{}".format(player_data[0])
            )

        # Select exactly 11 players
        self.model.Add(sum(self._variables_id.values()) == self.team_size)

        # Make sure a player is selected only once
        player_names = list(set([player_data[1] for player_data in self.data]))
        for player_name in player_names:
            single_player_variables = [
                var
                for var, data in zip(self._variables_id.values(), self.data)
                if data[1] == player_name
            ]
            self.model.Add(sum(single_player_variables) <= 1)

    def _build_rating_constraint(self, minimum_team_rating: int) -> None:

        # Constants
        all_ratings = [player_data[2] for player_data in self.data]
        min_rating = min(all_ratings)
        max_rating = max(all_ratings)
        diff_rating = max_rating - min_rating

        # Variables
        variable_base_rating = self.model.NewIntVar(
            min_rating * self.team_size,
            max_rating * self.team_size,
            "baserating",
        )
        variables_excess_rating = {}
        variables_max_excess_rating = {}
        variables_max_excess_rating_masked = {}
        for ind, player_data in enumerate(self.data):
            variables_excess_rating[ind] = self.model.NewIntVar(
                -diff_rating * self.team_size,
                diff_rating * self.team_size,
                "excess_rating_{}".format(player_data[0]),
            )
            variables_max_excess_rating[ind] = self.model.NewIntVar(
                0,
                diff_rating * self.team_size,
                "max_excess_rating_{}".format(player_data[0]),
            )
            variables_max_excess_rating_masked[ind] = self.model.NewIntVar(
                0,
                diff_rating * self.team_size,
                "max_excess_rating_masked_{}".format(player_data[0]),
            )

        # Constraints
        # Establish base rating
        self.model.Add(
            sum(
                [
                    selected * rating
                    for selected, rating in zip(
                        self._variables_id.values(), all_ratings
                    )
                ]
            )
            == variable_base_rating
        )
        # Establish excess ratings
        for ind, var in enumerate(self._variables_id.values()):
            player_rating = self.data[ind][2]
            self.model.Add(
                variables_excess_rating[ind]
                == player_rating * self.team_size - variable_base_rating
            ).OnlyEnforceIf(var)
            # Remove negative excess ratings
            self.model.AddMaxEquality(
                variables_max_excess_rating[ind],
                [variables_excess_rating[ind], 0],
            )
            # Mask excess rating with selected players
            self.model.AddMultiplicationEquality(
                variables_max_excess_rating_masked[ind],
                [variables_max_excess_rating[ind], var],
            )
        # Add excess ratings of selected players to base rating
        self.model.Add(
            variable_base_rating * self.team_size
            + sum(variables_max_excess_rating_masked.values())
            >= minimum_team_rating * self.team_size**2
        )

    def _build_chemistry_constraint(self) -> None:
        pass

    def _build_feature_constraint(self) -> None:
        pass

    def _build_cost_constraint(self, max_cost: int) -> None:
        player_costs = [player_data[6] for player_data in self.data]
        self.model.Add(
            sum(
                [
                    var * cost
                    for var, cost in zip(
                        self._variables_id.values(), player_costs
                    )
                ]
            )
            <= max_cost
        )

    def _build_minimization(self) -> None:
        player_costs = [player_data[6] for player_data in self.data]
        self.model.Minimize(
            sum(
                [
                    var * cost
                    for var, cost in zip(
                        self._variables_id.values(), player_costs
                    )
                ]
            )
        )

    def solve_with_time_limit(
        self,
    ) -> None:

        self.solve()

    def solve(self, time_limit: int = None) -> None:
        # TODO: IMPROVE OUTPUT FORMAT AND INFORMATION; INCLUDE POSITIONING AND CHEMISTRY
        # TODO: FIGURE OUT HOW TO GET BEST SOLUTION AFTER SPECIFIC TIME LIMIT

        if time_limit is not None:
            self.solver.parameters.max_time_in_seconds = time_limit

        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL:
            print("Optimal solution found!")
            print("Cost: {}".format(self.solver.ObjectiveValue()))
            print("Players:")

            mask = [
                self.solver.Value(var) == 1
                for var in self._variables_id.values()
            ]
            selected_players = [
                player_data for player_data, m in zip(self.data, mask) if m
            ]
            total_cost = sum(
                [player_data[6] for player_data in selected_players]
            )
            ratings = [player_data[2] for player_data in selected_players]

            # find the longest string in each column of self.data
            longest_strings = [0] * len(selected_players[0])
            for player_data in selected_players:
                for i, s in enumerate(player_data):
                    longest_strings[i] = max(longest_strings[i], len(str(s)))
            for player_data in selected_players:
                print(
                    " ".join(
                        str(s).rjust(l)
                        for s, l in zip(player_data, longest_strings)
                    )
                )

            # print(
            #     "Selected:",
            #     [
            #         solver.Value(v)
            #         for v, m in zip(
            #             variables_playerpositioncorrect.values(), mask
            #         )
            #         if m
            #     ],
            # )
            # print(
            #     "Chemistry:",
            #     [
            #         solver.Value(v)
            #         for v, m in zip(
            #             variables_playerchemistry.values(), mask
            #         )
            #         if m
            #     ],
            # )

            print("Total cost: {}".format(total_cost))
            print("Team rating: {}".format(team_rating(ratings)))
            # print("Team chemistry: {}".format(team_chemistry(selected_players)))
        else:
            print("No solution found.")

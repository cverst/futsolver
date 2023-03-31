from ortools.sat.python import cp_model
import json
from typing import List, Union
from utils.stats import team_rating
import time


FORMATION_FILE = "../src/formations.json"


class SBCSolver:
    def __init__(
        self,
        data: List[List[Union[int, str, list]]],
        formation: str = "442",
    ) -> None:

        self.data = data
        self.formation = formation

        self.team_size = None
        self.formation_list = None

        self._variables_id = None
        self._variables_player_position = None
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
            minimum_chemistry (int): Minimum chemistry.
            minimize (bool): Whether to minimize the cost of the team.
            maximum_cost (int): Maximum cost of the team.
            categorical_constraints (list): Minimum and maximum counts for
                categories. The extent makes the minimum constraint for all
                categories ("all") or for a single category ("single").

                Example:
                [
                    [feature_index_1, min_count_1, max_count_1, extent_1]
                    [feature_index_2, min_count_2, max_count_2, extent_2]
                    ...
                ]
            minimum_rating_count (list): Minimum number of players with a
                rating greater than or equal to specified rating.

                Example:
                [min_count, rating]
        """

        start_time = time.time()

        if constraints is None:
            constraints = {}
        self._constraints = constraints

        self._build_base_constraint()

        if "minimum_team_rating" in constraints:
            self._build_rating_constraint()

        if "minimum_chemistry" in constraints:
            self._build_chemistry_constraint()

        if "categorical_constraints" in constraints:
            for con in constraints["categorical_constraints"]:
                self._build_feature_constraint(con)
        
        if "count_constraints" in constraints:
            for con in constraints["count_constraints"]:
                self._build_count_constraint(con)

        if "minimum_rating_count" in constraints:
            self._build_minimum_rating_count_constraint()

        if "maximum_cost" in constraints:
            self._build_cost_constraint()

        if "minimize" in constraints:
            self._build_minimization()

        end_time = time.time()
        print("Build time:", end_time - start_time)

    def _build_base_constraint(self) -> None:

        # Variables
        self._variables_id = {}
        for index, player_data in enumerate(self.data):
            self._variables_id[index] = self.model.NewBoolVar(
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

    def _build_rating_constraint(self) -> None:

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
        for index, player_data in enumerate(self.data):
            variables_excess_rating[index] = self.model.NewIntVar(
                -diff_rating * self.team_size,
                diff_rating * self.team_size,
                "excess_rating_{}".format(player_data[0]),
            )
            variables_max_excess_rating[index] = self.model.NewIntVar(
                0,
                diff_rating * self.team_size,
                "max_excess_rating_{}".format(player_data[0]),
            )
            variables_max_excess_rating_masked[index] = self.model.NewIntVar(
                0,
                diff_rating * self.team_size,
                "max_excess_rating_masked_{}".format(player_data[0]),
            )

        # Constraints
        # Establish base rating
        base_rating = sum(
            [
                selected * rating
                for selected, rating in zip(
                    self._variables_id.values(), all_ratings
                )
            ]
        )
        self.model.Add(base_rating == variable_base_rating)
        # Establish excess ratings
        for index, var in enumerate(self._variables_id.values()):
            player_rating = self.data[index][2]
            self.model.Add(
                variables_excess_rating[index]
                == player_rating * self.team_size - variable_base_rating
            ).OnlyEnforceIf(var)
            # Remove negative excess ratings
            self.model.AddMaxEquality(
                variables_max_excess_rating[index],
                [variables_excess_rating[index], 0],
            )
            # Mask excess rating with selected players
            self.model.AddMultiplicationEquality(
                variables_max_excess_rating_masked[index],
                [variables_max_excess_rating[index], var],
            )
        # Add excess ratings of selected players to base rating
        self.model.Add(
            variable_base_rating * self.team_size
            + sum(variables_max_excess_rating_masked.values())
            >= self._constraints["minimum_team_rating"] * self.team_size**2
        )

    def _build_chemistry_constraint(self) -> None:
        # TODO: CREATE BOOLEANS FOR PREFERRED PLAYER POSITIONS HERE AND NOT IN GET_DATA FUNCTION. SEE HOW CLUBS ARE CALCULATED IN CHEMISTRY CONSTRAINT
        # TODO: REALLY NEEDS TO SPEED UP. FIND A SOLUTION WITH FEWER CONSTRAINTS.
        # Constants
        MAP_POSITION_TO_COLUMN = {
            "CAM": 10,
            "CB": 11,
            "CDM": 12,
            "CF": 13,
            "CM": 14,
            "GK": 15,
            "LB": 16,
            "LM": 17,
            "LW": 18,
            "LWB": 19,
            "RB": 20,
            "RM": 21,
            "RW": 22,
            "RWB": 23,
            "ST": 24,
        }
        MAX_CHEMISTRY_PER_PLAYER = 3

        # Variables
        self._variables_player_position = {}
        variables_player_position_correct = {}
        variables_potential_player_chemistry_raw = {}
        variables_potential_player_chemistry = {}
        variables_player_chemistry = {}
        variables_player_chemistry_selected = {}
        for index, player_data in enumerate(self.data):
            variables_player_position_correct[index] = self.model.NewBoolVar(
                "player_position_correct_{}".format(player_data[0])
            )
            for position in self.formation_list:
                self._variables_player_position[
                    (index, position)
                ] = self.model.NewBoolVar(
                    "player_position_{}_{}".format(player_data[0], position)
                )
            variables_potential_player_chemistry_raw[
                index
            ] = self.model.NewIntVar(
                0,
                MAX_CHEMISTRY_PER_PLAYER * 3,
                "potential_player_chemistry_raw",
            )
            variables_potential_player_chemistry[index] = self.model.NewIntVar(
                0, MAX_CHEMISTRY_PER_PLAYER, "potential_player_chemistry"
            )
            variables_player_chemistry[index] = self.model.NewIntVar(
                0, MAX_CHEMISTRY_PER_PLAYER, "player_chemistry"
            )
            variables_player_chemistry_selected[index] = self.model.NewIntVar(
                0, MAX_CHEMISTRY_PER_PLAYER, "player_chemistry_selected"
            )
        variables_club_count = {}
        variables_club_chemistry_division = {}
        variables_club_chemistry = {}
        clubs = list(set([player_data[7] for player_data in self.data]))
        for club in clubs:
            variables_club_count[club] = self.model.NewIntVar(
                0, self.team_size, "club_count_{}".format(club)
            )
            variables_club_chemistry_division[club] = self.model.NewIntVar(
                0, 4, "club_chemistry_division_{}".format(club)
            )
            variables_club_chemistry[club] = self.model.NewIntVar(
                0, MAX_CHEMISTRY_PER_PLAYER, "club_chemistry"
            )
        variables_league_count = {}
        variables_league_chemistry_division = {}
        variables_league_chemistry = {}
        leagues = list(set([player_data[8] for player_data in self.data]))
        for league in leagues:
            variables_league_count[league] = self.model.NewIntVar(
                0, self.team_size, "league_count_{}".format(league)
            )
            variables_league_chemistry_division[league] = self.model.NewIntVar(
                0, 4, "league_chemistry_division_{}".format(league)
            )
            variables_league_chemistry[league] = self.model.NewIntVar(
                0, MAX_CHEMISTRY_PER_PLAYER, "league_chemistry"
            )
        variables_country_count = {}
        variables_country_chemistry_division = {}
        variables_country_chemistry = {}
        countries = list(set([player_data[9] for player_data in self.data]))
        for country in countries:
            variables_country_count[country] = self.model.NewIntVar(
                0, self.team_size, "country_count_{}".format(country)
            )
            variables_country_chemistry_division[
                country
            ] = self.model.NewIntVar(
                0, 4, "country_chemistry_division_{}".format(country)
            )
            variables_country_chemistry[country] = self.model.NewIntVar(
                0, MAX_CHEMISTRY_PER_PLAYER, "country_chemistry"
            )

        # Constraints
        # Make sure that a selected player has a position
        for index, var in enumerate(self._variables_id.values()):
            n_players_selected_per_position = sum(
                [
                    self._variables_player_position[(index, position)]
                    for position in self.formation_list
                ]
            )
            self.model.Add(n_players_selected_per_position == 1).OnlyEnforceIf(
                var
            )
        # Make sure each position has exactly one player
        for position in self.formation_list:
            n_positions_selected_per_player = sum(
                [
                    self._variables_player_position[(id, position)]
                    for id in self._variables_id.keys()
                ]
            )
            self.model.Add(n_positions_selected_per_player == 1)
        # Calculate if chemistry should be counted
        for index, (id, var) in enumerate(self._variables_id.items()):
            for position in self.formation_list:
                self.model.Add(
                    variables_player_position_correct[index]
                    == self._variables_player_position[(id, position)]
                    * self.data[index][
                        MAP_POSITION_TO_COLUMN[position.split("_")[0]]
                    ]
                ).OnlyEnforceIf(
                    self._variables_player_position[(id, position)]
                )
        # Count number of players per club
        # [0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3] -> chemistry
        # [0, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4] -> (2 * (n_players + 1)) // 5
        for club, var in variables_club_count.items():
            club_bool = [player_data[7] == club for player_data in self.data]
            players_selected_for_club = sum(
                [
                    var * b
                    for var, b in zip(self._variables_id.values(), club_bool)
                ]
            )
            self.model.Add((players_selected_for_club + 1) * 2 == var)
            self.model.AddDivisionEquality(
                variables_club_chemistry_division[club],
                var,
                5,
            )
            self.model.AddMinEquality(
                variables_club_chemistry[club],
                [
                    variables_club_chemistry_division[club],
                    MAX_CHEMISTRY_PER_PLAYER,
                ],
            )
        # Count number of players per league
        # [0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3] -> chemistry
        # [0, 0, 1, 1, 2, 2, 2, 3, 3, 4, 4] -> (2 * n_players) // 5
        for league, var in variables_league_count.items():
            league_bool = [
                player_data[8] == league for player_data in self.data
            ]
            players_selected_for_league = sum(
                [
                    var * b
                    for var, b in zip(self._variables_id.values(), league_bool)
                ]
            )
            self.model.Add((players_selected_for_league) * 2 == var)
            self.model.AddDivisionEquality(
                variables_league_chemistry_division[league],
                var,
                5,
            )
            self.model.AddMinEquality(
                variables_league_chemistry[league],
                [
                    variables_league_chemistry_division[league],
                    MAX_CHEMISTRY_PER_PLAYER,
                ],
            )
        # Count number of players per country
        # [0, 0, 0, 1, 1, 2, 2, 2, 3, 3, 3] -> chemistry
        # [0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4] -> (n_players + 1) // 3
        for country, var in variables_country_count.items():
            country_bool = [
                player_data[9] == country for player_data in self.data
            ]
            players_selected_for_country = sum(
                [
                    var * b
                    for var, b in zip(
                        self._variables_id.values(), country_bool
                    )
                ]
            )
            self.model.Add((players_selected_for_country + 1) == var)
            self.model.AddDivisionEquality(
                variables_country_chemistry_division[country],
                var,
                3,
            )
            self.model.AddMinEquality(
                variables_country_chemistry[country],
                [
                    variables_country_chemistry_division[country],
                    MAX_CHEMISTRY_PER_PLAYER,
                ],
            )
        # Calculate potential chemistry per player
        for index, var in enumerate(self._variables_id.values()):
            self.model.Add(
                variables_potential_player_chemistry_raw[index]
                == variables_club_chemistry[self.data[index][7]]
                + variables_league_chemistry[self.data[index][8]]
                + variables_country_chemistry[self.data[index][9]]
            ).OnlyEnforceIf(var)
            self.model.AddMinEquality(
                variables_potential_player_chemistry[index],
                [
                    variables_potential_player_chemistry_raw[index],
                    MAX_CHEMISTRY_PER_PLAYER,
                ],
            )
        # Calculate chemistry
        for index, var in enumerate(self._variables_id.values()):
            self.model.AddMultiplicationEquality(
                variables_player_chemistry[index],
                [
                    variables_potential_player_chemistry[index],
                    variables_player_position_correct[index],
                ],
            )
            self.model.AddMultiplicationEquality(
                variables_player_chemistry_selected[index],
                [
                    variables_player_chemistry[index],
                    var,
                ],
            )
        self.model.Add(
            sum(variables_player_chemistry_selected.values())
            >= self._constraints["minimum_chemistry"]
        )

    def _build_feature_constraint(
        self, constraint: Union[list, tuple]
    ) -> None:
        # constraint = (feature_index, mininum, maximum, type)

        # Constants
        feature_index = constraint[0]
        minimum = constraint[1]
        maximum = constraint[2]
        constraint_type = constraint[3]

        # Variables
        variables_category_in_selection = {}
        for player_data in self.data:
            category = player_data[feature_index]
            if category not in variables_category_in_selection:
                variables_category_in_selection[
                    category
                ] = self.model.NewBoolVar(
                    "feature{}_{}".format(feature_index, category)
                )

        # Constraints
        variables_category_count = {}
        variables_category_count_max = self.model.NewIntVar(
            0, self.team_size, "feature{}_count_max".format(feature_index)
        )
        for category, var in variables_category_in_selection.items():
            feature_total = sum(
                [
                    self._variables_id[index]
                    for index, player_data in enumerate(self.data)
                    if player_data[feature_index] == category
                ]
            )
            self.model.Add(feature_total <= maximum)
            if constraint_type == "single":
                variables_category_count[category] = self.model.NewIntVar(
                    0,
                    self.team_size,
                    "feature{}_{}_count".format(feature_index, category),
                )
            elif constraint_type == "all":
                self.model.Add(feature_total >= minimum).OnlyEnforceIf(var)
                self.model.Add(feature_total == 0).OnlyEnforceIf(var.Not())
            else:
                raise ValueError(
                    "Unknown constraint type: {}".format(constraint_type)
                )
        if constraint_type == "single":
            self.model.AddMaxEquality(
                variables_category_count_max, variables_category_count.values()
            )
            self.model.Add(variables_category_count_max >= minimum)
    
    def _build_count_constraint(self, constraint: Union[list, tuple]) -> None:
        # constraint = (feature_index, minimum, maximum)

        # Constants
        feature_index = constraint[0]
        minimum = constraint[1]
        maximum = constraint[2]

        # Constraints
        for category in list(set([player_data[feature_index] for player_data in self.data])):
            category_total = sum(
                [
                    self._variables_id[index]
                    for index, player_data in enumerate(self.data)
                    if player_data[feature_index] == category
                ]
            )
            self.model.Add(category_total <= maximum)
            self.model.Add(category_total >= minimum)

    def _build_minimum_rating_count_constraint(self) -> None:
        # constraint (count, minimum)

        # Constants
        count = self._constraints["minimum_rating_count"][0]
        minimum = self._constraints["minimum_rating_count"][1]

        # Variables
        ratings = [player_data[2] for player_data in self.data]
        ratings_larger_than_minimum = [rating >= minimum for rating in ratings]
        variable_minimum_rating_counted = self.model.NewIntVar(
            0, self.team_size, "minimum_rating_counted"
        )
        self.model.Add(
            sum(
                [
                    var * b
                    for var, b in zip(
                        self._variables_id.values(),
                        ratings_larger_than_minimum,
                    )
                ]
            )
            == variable_minimum_rating_counted
        )
        self.model.Add(variable_minimum_rating_counted >= count)

    def _build_cost_constraint(self) -> None:
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
            <= self._constraints["maximum_cost"]
        )

    def _build_minimization(self) -> None:
        # TODO: TEST IF MINIMIZATION CAN BE TIME LIMITED
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

        start_time = time.time()

        status = self.solver.Solve(self.model)

        end_time = time.time()
        print("Solve time:", end_time - start_time)
        print()

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
            print()

            if self._variables_player_position is None:
                print("No position constraints.")
            else:
                players_by_position = [
                    key
                    for key, var in self._variables_player_position.items()
                    if self.solver.Value(var)
                ]
                players_by_position = [
                    list(item)[::-1] for item in players_by_position
                ]
                players_by_position = sorted(
                    players_by_position,
                    key=lambda x: self.formation_list.index(x[0]),
                )
                players_by_position = [
                    (pos, self.data[index][1])
                    for pos, index in players_by_position
                ]
                for pos, player in players_by_position:
                    print(
                        pos.rjust(longest_strings[0])
                        + " : "
                        + player.ljust(longest_strings[1])
                    )
                print()

            print("Total cost: {}".format(total_cost))
            print("Team rating: {}".format(team_rating(ratings)))
            # print("Team chemistry: {}".format(team_chemistry(selected_players)))
        else:
            print("No solution found.")

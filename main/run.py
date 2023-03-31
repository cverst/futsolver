import random
from solver import SBCSolver
from utils.data import get_data
import time

DATA_PATH = "../data/Fifa 23 Fut Players.csv"

CONSTRAINTS = {
    "minimum_team_rating": 80,
    "minimum_chemistry": 20,
    # "minimize": True,
    # "maximum_cost": 2200,
    "categorical_constraints": [
        # [8, 5, 5, "all"],
        [7, 0, 2, "all"],
        # [8, 5, 5, "all"],
    ],
    "count_constraints": [
        [8, 5, 5],
        [9, 6, 6],
    ]
    # "minimum_rating_count": [7, 75]
}

FORMATION = "442"


def run():
    print()
    print("Start time:", time.strftime("%H:%M:%S", time.localtime()))

    data = get_data(DATA_PATH)

    # TODO: FIGURE OUT BETTER WAY OF LIMITING SEARCH SPACE. MAYBE CALCULATE ALL RATING COMBINATIONS AND THEN FILTER OUT WHERE MEDIAN PRICES ARE LARGER THAN NAIVE MEDIAN PRICE?
    # Remove players more than 5 rating points above the minimum team rating
    # data = [
    #     player_data
    #     for player_data in data
    #     if player_data[2] <= CONSTRAINTS["minimum_team_rating"] + 4 and player_data[2] >= CONSTRAINTS["minimum_team_rating"] - 10
    # ]

    # Randomly select 5% of rows from data to speed up testing
    # random.seed(42)
    # data = random.sample(data, int(len(data) * 0.02))

    print("Number of players:", len(data))

    sbc_solver = SBCSolver(data, formation=FORMATION)

    sbc_solver.build(CONSTRAINTS)

    # sbc_solver.solve(time_limit=10)
    sbc_solver.solve()

    print("End time:", time.strftime("%H:%M:%S", time.localtime()))
    print()


if __name__ == "__main__":
    run()

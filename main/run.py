import random
from solver import SBCSolver
from utils.data import get_data
import datetime


DATA_PATH = "../data/Fifa 23 Fut Players.csv"

CONSTRAINTS = {
    "minimum_team_rating": 75,
}


def run():
    print("Start time:", datetime.datetime.now().strftime("%H:%M:%S"))

    data = get_data(DATA_PATH)

    # Randomly select 5% of rows from data to speed up testing
    data = random.sample(data, int(len(data) * 0.1))

    sbc_solver = SBCSolver(data, formation="442", minimize=False)

    sbc_solver.build(CONSTRAINTS)

    # sbc_solver.solve(time_limit=10)
    sbc_solver.solve()

    print("End time:", datetime.datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    run()

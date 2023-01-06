from ortools.linear_solver import pywraplp
import pandas as pd


def get_data():
    df = pd.read_csv("../Fifa 22 Fut Players.csv")

    # Change price to numeric
    def price_to_numeric(row):
        price_str = row["PS"]
        if price_str[-1] == "M":
            price = int(float(price_str[:-1]) * 1e6)
        elif price_str[-1] == "K":
            price = int(float(price_str[:-1]) * 1e3)
        else:
            price = int(price_str)
        return price

    df.loc[:, "PS"] = df.apply(price_to_numeric, axis=1)

    # Remove untradable entries (entries that have price 0)
    df = df.query("PS != 0").reset_index(drop=True)
    return df


df = get_data()

df = df.drop_duplicates(subset=["Name"])
df = df.loc[:, ["Name", "Ratings", "PS", "Club"]]

# df = df.loc[:5000, :]
df = df.query("Club in ['AZ', 'FC Utrecht', 'Feyenoord', 'PSV', 'Ajax', 'FC Twente']")

print(df.sort_values(by=["PS"], ascending=True).head(11))


solver = pywraplp.Solver("team", pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)


# Variables

variables_name = {}
variables_club = {}

for _, row in df.iterrows():
    variables_name[row["Name"]] = solver.IntVar(0, 1, "x_{}".format(row["Name"]))
    if row["Club"] not in variables_club:
        variables_club[row["Club"]] = solver.IntVar(
            0, solver.infinity(), "y_{}".format(row["Club"])
        )

# Constraints

# Link player <-> club
for club, var in variables_club.items():
    constraint = solver.Constraint(0, solver.infinity())
    constraint.SetCoefficient(var, 1)
    for player in df.query("`Club`==@club").loc[:, "Name"]:
        # TODO: I DON'T GET THIS COEFFICIENT HERE
        constraint.SetCoefficient(variables_name[player], -1)

MAX_PLAYERS_PER_CLUB = 3
for club, var in variables_club.items():
    constraint = solver.Constraint(0, MAX_PLAYERS_PER_CLUB)
    constraint.SetCoefficient(var, 1)


# Set team size
TEAM_SIZE = 11
constraint_team_size = solver.Constraint(TEAM_SIZE, TEAM_SIZE)
for player in variables_name.values():
    constraint_team_size.SetCoefficient(player, 1)

# Objective
objective = solver.Objective()
objective.SetMinimization()

for _, row in df.iterrows():
    objective.SetCoefficient(variables_name[row["Name"]], row["PS"])

# Solve and retrieve solution
solver.Solve()

chosen_players = [
    key for key, variable in variables_name.items() if variable.solution_value() > 0.5
]

print(df[df.loc[:, "Name"].isin(chosen_players)])

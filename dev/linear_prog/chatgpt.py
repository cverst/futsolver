from ortools.linear_solver import pywraplp
import pandas as pd


def get_data():
    df = pd.read_csv("Fifa 22 Fut Players.csv")

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
# df = df.query("Club in ['AZ', 'Feyenoord', 'PSV', 'Ajax']")

# Extract input parameters
players = df.loc[:, "Name"].values
clubs = pd.Series(df.loc[:, "Club"].values, df.loc[:, "Name"]).to_dict()
costs = pd.Series(df.loc[:, "PS"].values, df.loc[:, "Name"]).to_dict()

# Create a solver and variables for each player
solver = pywraplp.Solver("team", pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)
# solver = pywraplp.Solver('CheapestPlayers', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

variables = {}
for player in players:
    variables[player] = solver.NumVar(0, 1, player)

# Create a dictionary to store the club variables
club_variables = {}
for club in clubs:
    club_variables[club] = solver.NumVar(0, 1, f"{club}_club")

# Create a dictionary to store the club count variables
club_count_variables = {}
for club in clubs:
    club_count_variables[club] = solver.NumVar(0, solver.infinity(), f"{club}_count")

# Set the objective to minimize the total cost of the players
objective = solver.Objective()
for player, cost in costs.items():
    objective.SetCoefficient(variables[player], cost)
objective.SetMinimization()

# Add constraints to select only 11 players and limit the number of players per club
TEAM_SIZE = 11
constraint = solver.Constraint(TEAM_SIZE, TEAM_SIZE)
for player in players:
    constraint.SetCoefficient(variables[player], 1)
    club = clubs[player]
    club_variables[club].SetCoefficient(variables[player], 1)
    club_count_variables[club].SetCoefficient(variables[player], 1)

MIN_PLAYERS_PER_CLUB = 2
MAX_PLAYERS_PER_CLUB = 3

for club in clubs:
    # solver.Add(club_count_variables[club] <= 3)
    solver.Add(
        MIN_PLAYERS_PER_CLUB <= club_count_variables[club] <= MAX_PLAYERS_PER_CLUB
    )

# # Add constraints to ensure that clubs with 2 or more players have at least 2 players in the group
# for club in clubs:
#     solver.Add(2 * club_variables[club] <= club_count_variables[club])

# Solve the problem
solution_status = solver.Solve()

# Print the cheapest players
if solution_status == pywraplp.Solver.OPTIMAL:
    print("Cheapest players:")
    for player, var in variables.items():
        if var.solution_value() == 1:
            print(f"{player}: {costs[player]}")

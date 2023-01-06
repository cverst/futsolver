from utils.data import get_data
from ortools.sat.python import cp_model

# ---------- PREPARATIONS ----------

df = get_data()

print("\n", "Ground truth:")
print(df.sort_values(by=["PS"], ascending=True).head(11))
print(
    "Minimum cost: {}\n".format(
        sum(df.sort_values(by=["PS"], ascending=True).head(11).loc[:, "PS"])
    )
)

ground_truth = sum(df.sort_values(by=["PS"], ascending=True).head(11).loc[:, "PS"])

model = cp_model.CpModel()


# ---------- PARAMETERS ----------
TEAM_SIZE = 11

MAX_PLAYERS_PER_CLUB = 5
MIN_PLAYERS_PER_CLUB = 2

MIN_TEAM_RATING = 75

# ---------- VARIABLES ----------

# Player selection variables
variables_name = {}
for _, row in df.iterrows():
    name = row["Name"]
    variables_name[name] = model.NewBoolVar("name_{}".format(name))

# Club selection variables
variables_club = {}
for _, row in df.iterrows():
    club = row["Club"]
    if club not in variables_club:
        variables_club[club] = model.NewBoolVar("club_{}".format(club))

# Rating variable
min_rating = df.loc[:, "Ratings"].min()
max_rating = df.loc[:, "Ratings"].max()
variable_rating = model.NewIntVar(min_rating, max_rating, "rating")
variables_excessrating = {}
for rating in range(min_rating, max_rating + 1):
    pass

# ---------- CONSTRAINTS ----------

# Select exactly 11 players
model.Add(sum(variables_name.values()) == TEAM_SIZE)

# Select a maximum number of players per club
for club, var in variables_club.items():
    model.Add(
        sum(
            [
                variables_name[player]
                for player in df.query("`Club`==@club").loc[:, "Name"]
            ]
        )
        <= MAX_PLAYERS_PER_CLUB
    )

# # Select a minimum number of players per club, but only enforce this for clubs with 1 or more players in the team
for club, var in variables_club.items():
    model.Add(
        sum(
            [
                variables_name[player]
                for player in df.query("`Club`==@club").loc[:, "Name"]
            ]
        )
        >= MIN_PLAYERS_PER_CLUB
    ).OnlyEnforceIf(var)
    model.Add(
        sum(
            [
                variables_name[player]
                for player in df.query("`Club`==@club").loc[:, "Name"]
            ]
        )
        == 0
    ).OnlyEnforceIf(var.Not())


# Select a team with minimum rating
model.Add(
    sum(
        [
            name * rating
            for name, rating in zip(variables_name.values(), df.loc[:, "Ratings"])
        ]
    )
    <= variable_rating * TEAM_SIZE
)

model.Add(
    sum(
        [
            name * rating
            for name, rating in zip(variables_name.values(), df.loc[:, "Ratings"])
        ]
    )
    >= MIN_TEAM_RATING * TEAM_SIZE
)


# # Limit cost to ground_truth + 5%
# MAX_COST = round(ground_truth * 1.05)
# model.Add(
#     sum([name * cost for name, cost in zip(variables_name.values(), df.loc[:, "PS"])])
#     <= MAX_COST
# )

# The following line can be used to find the best solution. However, we want o find a range of solutions for now.
model.Minimize(
    sum([name * cost for name, cost in zip(variables_name.values(), df.loc[:, "PS"])])
)

# ---------- SOLVER ----------

solver = cp_model.CpSolver()
# solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model)

# ---------- RESULTS ----------
if status == cp_model.OPTIMAL:
    print("Optimal solution found!")
    print("Cost: {}".format(solver.ObjectiveValue()))
    print("Players:")
    mask = [solver.Value(variables_name[name]) == 1 for name in variables_name]
    print(df.loc[mask, :])
    print("Total cost: {}".format(sum(df.loc[mask, "PS"])))
    print("Rating threshold: {}".format(solver.Value(variable_rating)))
else:
    print("No solution found.")

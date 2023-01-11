from ortools.sat.python import cp_model
import datetime
from utils.data import get_data
from utils.stats import team_rating


print(datetime.datetime.now())

# ---------- PREPARATIONS ----------

df = get_data()

# Only keep players with rating in range 65 - 85
# df = df.query("65 <= Ratings <= 85")
df = df.query("League == 'Eredivisie'")

print("Number of players: ", len(df))

model = cp_model.CpModel()


# ---------- PARAMETERS ----------
TEAM_SIZE = 11

MAX_PLAYERS_PER_CLUB = 3
MIN_PLAYERS_PER_CLUB = 2

MIN_TEAM_RATING = 76

MAX_COST = 15000

# ---------- VARIABLES ----------

# Player selection variables
variables_id = {}
player_names = []
for _, row in df.iterrows():
    id = row["ID"]
    name = row["Name"]
    variables_id[id] = model.NewBoolVar("id_{}".format(id))
    if name not in player_names:
        player_names.append(name)

# Club selection variables
variables_club = {}
for _, row in df.iterrows():
    club = row["Club"]
    if club not in variables_club:
        variables_club[club] = model.NewBoolVar("club_{}".format(club))

# Rating variables
min_rating = df.loc[:, "Ratings"].min()
max_rating = df.loc[:, "Ratings"].max()
variable_baserating = model.NewIntVar(
    min_rating * TEAM_SIZE, max_rating * TEAM_SIZE, "baserating"
)
variables_excessrating = {}
variables_maxexcessrating = {}
variables_maxexcessratingmultiplied = {}
diff_rating = max_rating - min_rating
for _, row in df.iterrows():
    id = row["ID"]
    variables_excessrating[id] = model.NewIntVar(
        -diff_rating * TEAM_SIZE,
        diff_rating * TEAM_SIZE,
        "excessrating_{}".format(id),
    )
    variables_maxexcessrating[id] = model.NewIntVar(
        0, diff_rating * TEAM_SIZE, "maxexcessrating_{}".format(id)
    )
    variables_maxexcessratingmultiplied[id] = model.NewIntVar(
        0, diff_rating * TEAM_SIZE, "maxexcessratingmultiplied_{}".format(id)
    )


# ---------- CONSTRAINTS ----------

# Select exactly 11 players
model.Add(sum(variables_id.values()) == TEAM_SIZE)

# Make sure a player is selected only once
for name in player_names:
    model.Add(
        sum(
            [
                variables_id[player]
                for player in df.query("`Name`==@name").loc[:, "ID"]
            ]
        )
        <= 1
    )

# Select a maximum number of players per club
for club, var in variables_club.items():
    model.Add(
        sum(
            [
                variables_id[player]
                for player in df.query("`Club`==@club").loc[:, "ID"]
            ]
        )
        <= MAX_PLAYERS_PER_CLUB
    )

# Select a minimum number of players per club, but only enforce this for clubs with 1 or more players in the team
for club, var in variables_club.items():
    model.Add(
        sum(
            [
                variables_id[player]
                for player in df.query("`Club`==@club").loc[:, "ID"]
            ]
        )
        >= MIN_PLAYERS_PER_CLUB
    ).OnlyEnforceIf(var)
    model.Add(
        sum(
            [
                variables_id[player]
                for player in df.query("`Club`==@club").loc[:, "ID"]
            ]
        )
        == 0
    ).OnlyEnforceIf(var.Not())


# Select a team with minimum rating
# TODO: CURRENTLY CALCULATED EACH RUN, BUT MAY BE BETTER DONE THROUGH LOOKUP TABLE
# Establish base rating
model.Add(
    sum(
        [
            selected * rating
            for selected, rating in zip(variables_id.values(), df.loc[:, "Ratings"])
        ]
    )
    == variable_baserating
)
# Establish all excess ratings
for id, var in variables_id.items():
    model.Add(
        variables_excessrating[id]
        == df.query("`ID`==@id").loc[:, "Ratings"].values[0] * TEAM_SIZE
        - variable_baserating
    ).OnlyEnforceIf(var)
    # Establish maximum excess rating to remove negative excess ratings
    model.AddMaxEquality(
        variables_maxexcessrating[id],
        [variables_excessrating[id], 0],
    )
    # Establish multiplication equalities for excess rating
    model.AddMultiplicationEquality(
        variables_maxexcessratingmultiplied[id],
        [variables_maxexcessrating[id], var],
    )

# Final constraint for minimum team rating:
# Add the excess ratings for selected players to the base rating multiplied by the team size
model.Add(
    variable_baserating * TEAM_SIZE + sum(variables_maxexcessratingmultiplied.values())
    >= MIN_TEAM_RATING * TEAM_SIZE * TEAM_SIZE
)

# Limit cost
model.Add(
    sum([id * cost for id, cost in zip(variables_id.values(), df.loc[:, "PS"])])
    <= MAX_COST
)

# The following line can be used to find the best solution. However, we want o find a range of solutions for now.
# model.Minimize(
#     sum([id * cost for id, cost in zip(variables_id.values(), df.loc[:, "PS"])])
# )

# ---------- SOLVER ----------

solver = cp_model.CpSolver()
# solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model)

# ---------- RESULTS ----------
if status == cp_model.OPTIMAL:
    print("Optimal solution found!")
    print("Cost: {}".format(solver.ObjectiveValue()))
    print("Players:")
    mask = [solver.Value(variables_id[id]) == 1 for id in variables_id]
    print(df.loc[mask, :])
    print("Total cost: {}".format(sum(df.loc[mask, "PS"])))
    print("Team rating: {}".format(team_rating(df.loc[mask, "Ratings"])))
else:
    print("No solution found.")

print(datetime.datetime.now())

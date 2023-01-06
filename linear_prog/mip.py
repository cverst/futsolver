from utils.data import get_data
from ortools.linear_solver import pywraplp

# ---------- PREPARATIONS ----------

df = get_data()

print("\n", "Ground truth:")
print(df.sort_values(by=["PS"], ascending=True).head(11))
print(
    "Minimum cost: {}\n".format(
        sum(df.sort_values(by=["PS"], ascending=True).head(11).loc[:, "PS"])
    )
)

solver = pywraplp.Solver("team", pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)


# ---------- VARIABLES ----------
# First create variables

variable_name = {}
for _, row in df.iterrows():
    variable_name[row["Name"]] = solver.IntVar(0, 1, "name_{}".format(row["Name"]))

variable_club = {}
for _, row in df.iterrows():
    if row["Club"] not in variable_club:
        variable_club[row["Club"]] = solver.IntVar(
            0, solver.infinity(), "club_{}".format(row["Club"])
        )

# ---------- CONSTRAINTS ----------
# Add constraints to the problem

# Link players to their clubs
for club, var in variable_club.items():
    constraint = solver.Constraint(1, solver.infinity())
    constraint.SetCoefficient(var, 1)
    for player in df.query("`Club`==@club").loc[:, "Name"]:
        constraint.SetCoefficient(variable_name[player], -1)
        
# Select exactly 11 players
TEAM_SIZE = 11
constraint_teamsize = solver.Constraint(TEAM_SIZE, TEAM_SIZE)
for player in variable_name.values():
    constraint_teamsize.SetCoefficient(player, 1)

# Select a maximum of 3 players per club
MAX_PLAYERS_PER_CLUB = 3
for club, var in variable_club.items():
    constraint = solver.Constraint(0, MAX_PLAYERS_PER_CLUB)
    constraint.SetCoefficient(var, 1)


# ---------- OBJECTIVE ----------
# Next define the objective function

objective = solver.Objective()
for _, row in df.iterrows():
    objective.SetCoefficient(variable_name[row["Name"]], row["PS"])
objective.SetMinimization()


# ---------- SOLVE ----------
# Solve the problem and retrieve the optimal solution

status = solver.Solve()
# assert status == pywraplp.Solver.OPTIMAL


# ---------- RESULTS ----------
# Print the selected players and their costs

print("Selected players:")
selected_players = [
    key for key, variable in variable_name.items() if variable.solution_value() == 1
]
print(df[df.loc[:, "Name"].isin(selected_players)])

# You can also print the minimum cost of the selected team.
print(f"Minimum cost: {objective.Value()}")

from ortools.sat.python import cp_model
import datetime
from utils.data import get_data
from utils.stats import team_rating


print(datetime.datetime.now())

# ---------- PREPARATIONS ----------

# TODO: MAYBE MOVE AWAY FROM PANDAS; TRICKY PART IS REPLACING QUERY IN THE CONSTRAINTS
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
MIN_TEAM_CHEMISTRY = 5

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

# Chemistry variables
variables_potentialplayerchemistryraw = {}
variables_potentialplayerchemistry = {}
variables_playerchemistry = {}
variables_clubcount = {}
variables_leaguecount = {}
variables_countrycount = {}
variables_clubchemistrydivision = {}
variables_leaguechemistrydivision = {}
variables_countrychemistrydivision = {}
variables_clubchemistry = {}
variables_leaguechemistry = {}
variables_countrychemistry = {}
MAX_CHEMISTRY_PER_PLAYER = 3
for _, row in df.iterrows():
    id = row["ID"]
    club = row["Club"]
    league = row["League"]
    country = row["Country"]
    variables_potentialplayerchemistryraw[id] = model.NewIntVar(
        0, MAX_CHEMISTRY_PER_PLAYER * 3, "playerchemistry_{}".format(id)
    )
    variables_potentialplayerchemistry[id] = model.NewIntVar(
        0, MAX_CHEMISTRY_PER_PLAYER, "playerchemistry_{}".format(id)
    )
    variables_playerchemistry[id] = model.NewIntVar(
        0, MAX_CHEMISTRY_PER_PLAYER, "playerchemistry_{}".format(id)
    )
    if club not in variables_clubcount:
        variables_clubcount[club] = model.NewIntVar(
            0, TEAM_SIZE, "clubcount_{}".format(club)
        )
        variables_clubchemistrydivision[club] = model.NewIntVar(
            0, TEAM_SIZE // 2, "clubchemistrydivision_{}".format(club)
        )
        variables_clubchemistry[club] = model.NewIntVar(
            0, MAX_CHEMISTRY_PER_PLAYER, "clubchemistry_{}".format(club)
        )
    if league not in variables_leaguecount:
        variables_leaguecount[league] = model.NewIntVar(
            0, TEAM_SIZE, "leaguecount_{}".format(league)
        )
        variables_leaguechemistrydivision[league] = model.NewIntVar(
            0, TEAM_SIZE // 2, "leaguechemistrydivision_{}".format(league)
        )
        variables_leaguechemistry[league] = model.NewIntVar(
            0, MAX_CHEMISTRY_PER_PLAYER, "leaguechemistry_{}".format(league)
        )
    if country not in variables_countrycount:
        variables_countrycount[country] = model.NewIntVar(
            0, TEAM_SIZE, "countrycount_{}".format(country)
        )
        variables_countrychemistrydivision[country] = model.NewIntVar(
            0, TEAM_SIZE // 2, "countrychemistrydivision_{}".format(country)
        )
        variables_countrychemistry[country] = model.NewIntVar(
            0, MAX_CHEMISTRY_PER_PLAYER, "countrychemistry_{}".format(country)
        )

FORMATION = [
    "GK",
    "RB",
    "CB_1",
    "CB_2",
    "LB",
    "RM",
    "CM_1",
    "CM_2",
    "LM",
    "ST_1",
    "ST_2",
]
variables_playerposition = {}
for _, row in df.iterrows():
    id = row["ID"]
    for position in FORMATION:
        variables_playerposition[(id, position)] = model.NewBoolVar(
            "playerposition_{}_{}".format(id, position)
        )

# ---------- CONSTRAINTS ----------

# Select exactly 11 players
model.Add(sum(variables_id.values()) == TEAM_SIZE)

# Make sure a player is selected only once
for name in player_names:
    model.Add(
        sum([variables_id[player] for player in df.query("`Name`==@name").loc[:, "ID"]])
        <= 1
    )

# Select a maximum number of players per club
for club, var in variables_club.items():
    model.Add(
        sum([variables_id[player] for player in df.query("`Club`==@club").loc[:, "ID"]])
        <= MAX_PLAYERS_PER_CLUB
    )

# Select a minimum number of players per club, but only enforce this for clubs with 1 or more players in the team
for club, var in variables_club.items():
    model.Add(
        sum([variables_id[player] for player in df.query("`Club`==@club").loc[:, "ID"]])
        >= MIN_PLAYERS_PER_CLUB
    ).OnlyEnforceIf(var)
    model.Add(
        sum([variables_id[player] for player in df.query("`Club`==@club").loc[:, "ID"]])
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


# Chemistry constraints
# Count number of players per club
for club, var in variables_clubcount.items():
    model.Add(
        sum([variables_id[player] for player in df.query("`Club`==@club").loc[:, "ID"]])
        == var
    )
    model.AddDivisionEquality(
        variables_clubchemistrydivision[club],
        var,
        2,
    )
    model.AddMinEquality(
        variables_clubchemistry[club],
        [
            variables_clubchemistrydivision[club],
            MAX_CHEMISTRY_PER_PLAYER,
        ],
    )
# Count number of players per league
for league, var in variables_leaguecount.items():
    model.Add(
        sum(
            [
                variables_id[player]
                for player in df.query("`League`==@league").loc[:, "ID"]
            ]
        )
        == var
    )
    model.AddDivisionEquality(
        variables_leaguechemistrydivision[league],
        var,
        2,
    )
    model.AddMinEquality(
        variables_leaguechemistry[league],
        [
            variables_leaguechemistrydivision[league],
            MAX_CHEMISTRY_PER_PLAYER,
        ],
    )
# Count number of players per country
for country, var in variables_countrycount.items():
    model.Add(
        sum(
            [
                variables_id[player]
                for player in df.query("`Country`==@country").loc[:, "ID"]
            ]
        )
        == var
    )
    model.AddDivisionEquality(
        variables_countrychemistrydivision[country],
        var,
        2,
    )
    model.AddMinEquality(
        variables_countrychemistry[country],
        [
            variables_countrychemistrydivision[country],
            MAX_CHEMISTRY_PER_PLAYER,
        ],
    )
# Calculate potential chemistry per player
for id, var in variables_id.items():
    model.Add(
        variables_potentialplayerchemistryraw[id]
        == variables_clubchemistry[df.query("`ID`==@id").loc[:, "Club"].values[0]]
        + variables_leaguechemistry[df.query("`ID`==@id").loc[:, "League"].values[0]]
        + variables_countrychemistry[df.query("`ID`==@id").loc[:, "Country"].values[0]]
    ).OnlyEnforceIf(var)
    model.AddMinEquality(
        variables_potentialplayerchemistry[id],
        [
            variables_potentialplayerchemistryraw[id],
            MAX_CHEMISTRY_PER_PLAYER,
        ],
    )
# Make sure each player has at most one position
for id, var in variables_id.items():
    model.Add(
        sum([variables_playerposition[(id, position)] for position in FORMATION]) <= 1
    )
# Make sure each position has exactly one player
for position in FORMATION:
    model.Add(
        sum([variables_playerposition[(id, position)] for id in df.loc[:, "ID"]]) == 1
    )
# TODO: NOW DO SOMETHING WITH THE POSITIONING COLUMNS FROM THE DATAFRAME

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
status = solver.Solve(model)


# ---------- RESULTS ----------
# print([solver.Value(v) for k, v in variables_id.items()])
print([solver.Value(v) for k, v in variables_playerposition.items()])

if status == cp_model.OPTIMAL:
    print("Optimal solution found!")
    print("Cost: {}".format(solver.ObjectiveValue()))
    print("Players:")
    mask = [solver.Value(variables_id[id]) == 1 for id in variables_id]
    print(df.loc[mask, ["Name", "Club", "Ratings", "PS"]])
    print("Total cost: {}".format(sum(df.loc[mask, "PS"])))
    print("Team rating: {}".format(team_rating(df.loc[mask, "Ratings"])))
else:
    print("No solution found.")

print(datetime.datetime.now())

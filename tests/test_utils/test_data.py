from utils.data import get_data


def test_get_data() -> None:

    DATA_FILE = "../../data/Fifa 23 Fut Players.csv"
    data = get_data(DATA_FILE)

    assert type(data) == list
    assert type(data[0]) == list

    # ["ID", "Name", "Ratings", "Position", "Version",
    #  "Type", "PS", "Club", "League", "Country",
    #  "CAM", "CB", "CDM", "CF", "CM",
    #  "GK", "LB", "LM", "LW", "LWB",
    #  "RB", "RM", "RW", "RWB", "ST"]
    assert type(data[0][0]) == int  # ID
    assert type(data[0][1]) == str  # Name
    assert type(data[0][2]) == int  # Ratings
    assert type(data[0][3]) == list  # Position
    assert type(data[0][4]) == str  # Version
    assert type(data[0][5]) == str  # Type
    assert type(data[0][6]) == int  # PS
    assert type(data[0][7]) == str  # Club
    assert type(data[0][8]) == str  # League
    assert type(data[0][9]) == str  # Country
    assert type(data[0][10]) == int  # CAM
    assert type(data[0][11]) == int  # CB
    assert type(data[0][12]) == int  # CDM
    assert type(data[0][13]) == int  # CF
    assert type(data[0][14]) == int  # CM
    assert type(data[0][15]) == int  # GK
    assert type(data[0][16]) == int  # LB
    assert type(data[0][17]) == int  # LM
    assert type(data[0][18]) == int  # LW
    assert type(data[0][19]) == int  # LWB
    assert type(data[0][20]) == int  # RB
    assert type(data[0][21]) == int  # RM
    assert type(data[0][22]) == int  # RW
    assert type(data[0][23]) == int  # RWB
    assert type(data[0][24]) == int  # ST

    assert "Icon" not in [player_data[4] for player_data in data]
    assert "Hero" not in [player_data[4] for player_data in data]
    assert "WCHero" not in [player_data[4] for player_data in data]

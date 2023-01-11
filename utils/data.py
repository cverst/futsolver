import pandas as pd


DATA_PATH = "../Fifa Fut Players.csv"


def load(path):
    df = pd.read_csv(path)

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

    return df


def clean(df):
    # Remove untradable entries (entries that have price 0)
    df = df.query("PS != 0").reset_index(drop=True)
    return df


def curate(df):
    # Only keep players with Version ending with "IF", or Version part of ["Rare, Normal"]
    df = df.query("Version.str.endswith('IF') | Version.isin(['Rare', 'Normal'])")

    # When a player has multiple Position, create a new row for each Position
    df.loc[:, "Position"] = df.apply(lambda row: row["Position"].split(","), axis=1)
    df = df.explode("Position")

    # Sort players by Ratings
    df = df.sort_values(by="Ratings", ascending=False)

    # Create unique ID for each player
    df.reset_index(drop=True, inplace=True)
    df.loc[:, "ID"] = df.index

    # Only keep relevant columns in right order
    df = df.loc[
        :,
        [
            "ID",
            "Name",
            "Ratings",
            "Position",
            "Version",
            "PS",
            "Club",
            "League",
            "Country",
        ],
    ]

    # One-hot encode Position
    # df = pd.get_dummies(df, columns=["Position"], prefix="", prefix_sep="")

    return df


def get_data():
    df = load(DATA_PATH)
    df = clean(df)
    df = curate(df)
    # print(df.columns)
    # print(df.head(60))
    return df

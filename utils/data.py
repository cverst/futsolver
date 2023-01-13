import pandas as pd


DATA_PATH = "../Fifa 23 Fut Players.csv"

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

    # Replace single and double spaces with a comma in Position column
    df.loc[:, "Position"] = df.apply(
        lambda row: row["Position"].replace(" ", ",").replace(",,", ","), axis=1
    )

    # Convert Position column to list of strings
    df.loc[:, "Position"] = df.apply(lambda row: row["Position"].split(","), axis=1)

    # Split Explosive and Controlled off from the Version column
    df.loc[:, "Version"] = df.apply(
        lambda row: row["Version"].split(" ")[0], axis=1
    )
    return df


def curate(df):
    # Only keep players with Version ending with "IF", or Version part of ["Rare, Normal"]
    df = df.query("Version.str.endswith('IF') | Version.isin(['Rare', 'Normal'])")

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

    # One-hot encode all lists of position indicators, i.e., ["ST", "CF"] to columns with names "ST" and "CF"
    df = pd.concat(
        [df, pd.get_dummies(df.loc[:, "Position"].apply(pd.Series).stack()).groupby(level=0).sum()],
        axis=1,
    )

    return df


def get_data():
    df = load(DATA_PATH)
    df = clean(df)
    df = curate(df)
    # print(df.columns)
    # print(df.head(60))
    return df

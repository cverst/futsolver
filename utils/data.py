import pandas as pd


DATA_PATH = "../Fifa 22 Fut Players.csv"


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
    df = df.drop_duplicates(subset=["Name"])
    df = df.loc[:, ["Name", "Ratings", "PS", "Club"]]
    df = df.query(
        "Club in ['AZ', 'FC Utrecht', 'Feyenoord', 'PSV', 'Ajax', 'FC Twente']"
    )
    df.reset_index(drop=True, inplace=True)
    return df


def get_data():
    df = load(DATA_PATH)
    df = clean(df)
    df = curate(df)
    return df

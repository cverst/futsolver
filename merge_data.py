import pandas as pd

DATA_PATH1 = "Fifa 22 Fut Players.csv"
DATA_PATH2 = "Fifa 23 Fut Players.csv"

# load both files
df1 = pd.read_csv(DATA_PATH1)
df2 = pd.read_csv(DATA_PATH2)

# merge the position column from df2 into df1 based on the name column
df1 = df1.merge(df2[["Name", "Position"]], on="Name", how="inner", suffixes=("_x", "_y"))

# drop the original position column
df1.drop("Position_x", axis=1, inplace=True)

# rename the new position column
df1.rename(columns={"Position_y": "Position"}, inplace=True)

# in the Position column, remove any spaces or double spaces and replace them with a comma
df1["Position"] = df1["Position"].str.replace(" ", ",").str.replace(",,", ",")

# if a value in the position column contains more than two commas, replace it with a NaN
df1.loc[:, "Position"] = df1.apply(lambda x: x["Position"] if len(x["Position"].split(",")) <= 3 else None, axis=1)

# drop any rows that have no value or NaN in the position column
df1.dropna(subset=["Position"], inplace=True)

# drop any duplicates based on Name and Version
df1.drop_duplicates(subset=["Name", "Version"], inplace=True)

# save the merged data
df1.to_csv("Fifa Fut Players.csv", index=False)

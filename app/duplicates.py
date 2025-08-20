import pandas as pd


def find_duplicates(data):
    if not data:
        return []

    df = pd.DataFrame(data)
    df["devicetime"] = pd.to_datetime(df["devicetime"], errors="coerce")

    duplicate_df = df[df.duplicated(subset=["deviceid", "devicetime"], keep=False)] # noqa

    # Convert to dict with count of each duplicate
    grouped = duplicate_df.groupby(["deviceid", "devicetime"]).size().reset_index(name="count") # noqa
    grouped["devicetime"] = grouped["devicetime"].dt.strftime("%Y-%m-%d %H:%M:%S") # noqa

    return grouped.to_dict(orient="records")

from datetime import timedelta
import pandas as pd


def floor_to_5min(dt):
    return dt - timedelta(
        minutes=dt.minute % 5,
        seconds=dt.second,
        microseconds=dt.microsecond
    )


def find_missing_intervals(data, interval_minutes=5):
    # Build DataFrame from raw Mongo documents
    df = pd.DataFrame(data)

    # Parse 'devicetime' (assumed stored as ISODate)
    df["devicetime"] = pd.to_datetime(df["devicetime"])

    # Floor every timestamp to nearest 5‑minute mark
    df["ts_floor"] = df["devicetime"].apply(floor_to_5min)

    # Sort
    df = df.sort_values("ts_floor").reset_index(drop=True)

    # Debug: print what you're actually working with
    # print("⏱️ Floored devicetimes:")
    # print(df["ts_floor"].to_list())

    # Build the full expected timeline
    start = df["ts_floor"].min()
    end = df["ts_floor"].max()
    expected = pd.date_range(start=start, end=end, freq=f"{interval_minutes}min") # noqa

    found = set(df["ts_floor"])
    missing = []
    for t in expected:
        if t not in found:
            missing.append({
                "missing_interval_start": t.strftime("%Y-%m-%d %H:%M:%S"),
                "missing_interval_end":   (t + timedelta(minutes=interval_minutes)).strftime("%Y-%m-%d %H:%M:%S") # noqa
            })

    # print("🛑 Missing intervals:")
    # print(missing)
    return missing

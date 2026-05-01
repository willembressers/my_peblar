import pandas as pd
from dotenv import dotenv_values

config = dotenv_values(".env")


def data(data, entity_id, now, end):
    """Convert Home Assistant statistic timestamps into readable datetimes."""
    df = pd.DataFrame(data.get(entity_id, []))
    df["start"] = pd.to_datetime(df["start"], unit="ms", utc=True).dt.tz_convert(
        now.astimezone().tzinfo
    )
    df["end"] = pd.to_datetime(df["end"], unit="ms", utc=True).dt.tz_convert(
        now.astimezone().tzinfo
    )

    # Day statistics start at local midnight, so the last day of the range
    # must be kept when its bucket starts exactly on `end`.
    df = df[df["start"].dt.tz_localize(None) <= end]
    return df


def both(charger_df, tariff_df):
    # combine
    df = pd.merge(charger_df, tariff_df)

    # add a date column
    df["date"] = pd.to_datetime(df["start"]).dt.date

    # drop rows where there was nothing charged
    df = df.loc[df["change"] > 0]

    # rename the columns
    df = df.rename(columns={"change": "usage", "max": "cost"})

    # add a small fee
    df["cost"] = df["cost"] + float(config.get("FEE", 0))

    # add the cost per kWh and calculate the total cost
    df["total"] = df["usage"] * df["cost"]

    # remove the unused
    df = df.drop(columns=["start", "end"])

    return df

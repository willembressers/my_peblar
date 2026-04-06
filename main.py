from datetime import datetime, timedelta

import pandas as pd
from dotenv import dotenv_values

from home_assistant import fetch, parse
from output.pdf import PDF

# from output import pdf

config = dotenv_values(".env")
OUTPUT_DIR = config.get("OUTPUT_DIR", "/tmp")
NOW = datetime.now()
INVOICE = NOW.strftime("%Y%m%d%H%M%S")


def get_timestamps():

    # get the first and last day of the previous month
    end = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=1
    )
    start = end.replace(day=1)

    # get the first and last day of the current month
    # start = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    return start, end


def calculate_daily_usage(df_charger, df_tariff):
    # ensure the state column is numeric
    df_charger["state"] = df_charger["state"].astype(float)
    df_tariff["electricity_price"] = df_tariff["electricity_price"].astype(int)

    # convert micro-euros to euros
    df_tariff["cost"] = df_tariff["electricity_price"] / 10000000

    # convert the last_changed column to datetime and extract the date
    df_charger["date"] = pd.to_datetime(df_charger["last_changed"]).dt.date
    df_tariff["date"] = pd.to_datetime(df_tariff["datetime"]).dt.date

    # group by date
    df_daily_charger = df_charger.groupby("date")["state"].agg(["min", "max"])
    df_daily_tariff = df_tariff.groupby("date")["cost"].agg(["max"])

    # rename the columns
    df_daily_charger.rename(columns={"min": "start", "max": "end"}, inplace=True)
    df_daily_tariff.rename(columns={"max": "cost"}, inplace=True)

    # combine the two dataframes on the date
    df_daily = pd.merge(df_daily_charger, df_daily_tariff, on="date", how="left")

    # calculate the usage by subtracting the min from the max
    df_daily["usage"] = df_daily["end"] - df_daily["start"]

    # add the cost per kWh and calculate the total cost
    df_daily["total"] = df_daily["usage"] * df_daily["cost"]

    # reset the index to get the date back as a column
    df_daily.reset_index(inplace=True)

    # # write to excel with 2 sheets: "raw" and "aggregations"
    # path = f"{OUTPUT_DIR}/{INVOICE}.xlsx"
    # with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
    #     df_charger.to_excel(writer, index=False, sheet_name="charger_data")
    #     df_tariff.to_excel(writer, index=False, sheet_name="tariff_data")
    #     df_daily.to_excel(writer, index=False, sheet_name="aggregations")
    # print(f"-> DATA:\t{path}")

    return df_daily


def main():

    # Get the period
    start, end = get_timestamps()

    # get the data
    charger_data = fetch.history(start, end, config.get("CHARGER_ENTITY_ID"))
    if charger_data is None or len(charger_data) == 0:
        print("Error: No charger_data received")
        return

    tariff_data = fetch.history(start, end, config.get("TARIFF_ENTITY_ID"))
    if tariff_data is None or len(tariff_data) == 0:
        print("Error: No tariff_data received")
        return

    # parse the charger_data into a charger_dataframe
    df_charger = parse.charger(charger_data)
    df_tariff = parse.tariff(tariff_data)

    # calculate the usage
    df_daily = calculate_daily_usage(df_charger, df_tariff)

    # generate the PDF
    pdf = PDF(config, f"{OUTPUT_DIR}/backoffice/{INVOICE}.pdf")
    # pdf = PDF(config, "test.pdf")
    pdf.title("FACTUUR", "Declaratie EV laden")
    pdf.header(
        data=[
            ["VAN", "FACTUUR"],
            ["Willem Bressers", f"Nummer: {INVOICE}"],
            ["De Pottenbakker 28", f"Datum: {NOW.strftime('%Y-%m-%d')}"],
            [
                "5506GC, Veldhoven",
                f"Periode: {start.strftime('%Y-%m-%d')} tot {end.strftime('%Y-%m-%d')}",
            ],
        ]
    )
    pdf.data(df_daily)
    pdf.summary(df_daily)
    pdf.build()


if __name__ == "__main__":
    main()

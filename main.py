from datetime import datetime, timedelta

import pandas as pd
from dotenv import dotenv_values
import requests
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

config = dotenv_values(".env")
OUTPUT_DIR = config.get('OUTPUT_DIR', '/tmp')
NOW = datetime.now()
INVOICE = NOW.strftime('%Y%m%d%H%M%S')

def get_timestamps():

    # get the first and last day of the previous month
    end = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start = end.replace(day=1)

    # # get the first and last day of the current month
    # start = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    return start, end

def get_history(start: str, end: str, entity_id: str):
    # get the history data from the API
    url = f"{config.get('BASE_URL')}/api/history/period/{start}"
    headers = {"Authorization": f"Bearer {config.get('TOKEN')}", "Content-Type": "application/json"}
    params = {"filter_entity_id": entity_id, "end_time": end}
    response = requests.get(url, headers=headers, params=params)

    # check for errors
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    return response.json()

def parse_charger(data):
    states = []

    for state in data[0]:
        
        # skip unavailable values
        if state['state'] == "unavailable":
            continue

        # unwrap the attributes into the main dict
        state.update(state.pop("attributes"))

        # collect the state
        states.append(state)
    
    return pd.DataFrame(states)

def parse_tariff(data):
    tariffs = []

    for state in data[0]:

        # skip unavailable values
        if state['state'] == "unavailable":
            continue

        for forcast in state['attributes']['forecast']:
            tariffs.append(forcast)

    return pd.DataFrame(tariffs)

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

    # write to excel with 2 sheets: "raw" and "aggregations"
    path = f"{OUTPUT_DIR}/{INVOICE}.xlsx"
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        df_charger.to_excel(writer, index=False, sheet_name="charger_data")
        df_tariff.to_excel(writer, index=False, sheet_name="tariff_data")
        df_daily.to_excel(writer, index=False, sheet_name="aggregations")
    print(f"-> DATA:\t{path}")

    return df_daily

def generate_pdf(df_daily, start, end):
    path = f"{OUTPUT_DIR}/{INVOICE}.pdf"
    total_amount = df_daily["total"].sum()

    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # ---- Header ----
    elements.append(Paragraph("<b>Declaratie laadkosten EV</b>", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(config.get('NAME', 'name'), styles["Normal"]))
    elements.append(Paragraph(config.get('ADDRESS', 'address'), styles["Normal"]))
    elements.append(Paragraph(f"{config.get('POSTAL_CODE', 'postal_code')}, {config.get('CITY', 'city')}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Factuur-nummer: {INVOICE}", styles["Normal"]))
    elements.append(Paragraph(f"Factuur-datum: {NOW.strftime('%Y-%m-%d')}", styles["Normal"]))
    elements.append(Paragraph(f"Periode: {start.strftime('%Y-%m-%d')} tot {end.strftime('%Y-%m-%d')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ---- Table ----
    data = [["Datum", "Aantal", "Tarief", "Bedrag"]]
    for _, row in df_daily.iterrows():
        data.append([
            row["date"].strftime("%Y-%m-%d"),
            f"{row['usage']:.2f} kWh",
            f"€ {row['cost']:.2f}",
            f"€ {row['total']:.2f}"
        ])

    data.append(["", "", "Totaal", f"€ {total_amount:.2f}"])
    table = Table(data, colWidths=[200, 100, 100, 100])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ('LINEABOVE', (0, 1), (-1, 1), 1, colors.grey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, -1), (-1, -1), 12),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    doc.build(elements)
    print(f"-> INVOICE:\t{path}")

def main():
    
    # Get the period
    start, end = get_timestamps()

    # get the data
    charger_data = get_history(start, end, config.get('CHARGER_ENTITY_ID'))
    if charger_data is None or len(charger_data) == 0:
        print("Error: No charger_data received")
        return

    tariff_data = get_history(start, end, config.get('TARIFF_ENTITY_ID'))
    if tariff_data is None or len(tariff_data) == 0:
        print("Error: No tariff_data received")
        return

    # parse the charger_data into a charger_dataframe
    df_charger = parse_charger(charger_data)
    df_tariff = parse_tariff(tariff_data)
    
    # calculate the usage
    df_daily = calculate_daily_usage(df_charger, df_tariff)

    # generate the PDF
    generate_pdf(df_daily, start, end)


if __name__ == "__main__":
    main()
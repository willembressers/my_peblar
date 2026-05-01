from datetime import datetime, timedelta

from dotenv import dotenv_values

from home_assistant import fetch, parse
from output.pdf import PDF

config = dotenv_values(".env")
OUTPUT_DIR = config.get("OUTPUT_DIR", "/tmp")
NOW = datetime.now()
INVOICE = NOW.strftime("%Y%m%d%H%M%S")


def get_timestamps():
    """Return the start and end of the previous month."""

    # get the first and last day of the previous month
    end = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=1
    )
    start = end.replace(day=1)

    return start, end


def main():
    """Open one WebSocket and fetch one week of statistics for two sensors."""
    charger_id = config.get("CHARGER_ENTITY_ID")
    tariff_id = config.get("TARIFF_ENTITY_ID")

    # get the period
    start, end = get_timestamps()

    # get the data
    charger_data, tariff_data = fetch.data(start, end, charger_id, tariff_id)

    # parse the data
    charger_df = parse.data(charger_data["result"], charger_id, NOW, end)
    tariff_df = parse.data(tariff_data["result"], tariff_id, NOW, end)
    df = parse.both(charger_df, tariff_df)

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
    pdf.data(df)
    pdf.summary(df)
    pdf.build()


if __name__ == "__main__":
    main()

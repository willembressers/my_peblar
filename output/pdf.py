from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    _baseFontName,
    _baseFontNameB,
    getSampleStyleSheet,
)
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PRIMARY_COLOR = colors.midnightblue
SECONDARY_COLOR = colors.lightslategray
ROW_DIVIDER_COLOR = colors.HexColor("#E3E3E3")
SUMMARY_BACKGROUND = colors.HexColor("#F6F8FC")
TOTAL_BACKGROUND = colors.HexColor("#E9EFF8")
VAT_RATE = 0.21

stylesheet = getSampleStyleSheet()
stylesheet.add(
    ParagraphStyle(
        name="Titel",
        parent=stylesheet["Normal"],
        fontName=_baseFontNameB,
        fontSize=18,
        leading=22,
        alignment=TA_LEFT,
        spaceAfter=1,
        textColor=PRIMARY_COLOR,
    ),
    alias="titel",
)
stylesheet.add(
    ParagraphStyle(
        name="SubTitel",
        parent=stylesheet["Normal"],
        fontName=_baseFontName,
        fontSize=10,
        leading=22,
        alignment=TA_LEFT,
        spaceAfter=10,
        textColor=SECONDARY_COLOR,
    ),
    alias="subtitel",
)


class PDF:
    elements = []

    def __init__(self, config, path):
        self.config = config
        self.doc = SimpleDocTemplate(path, pagesize=A4)
        self.styles = stylesheet

    def title(self, title, subtitle):
        self.elements.append(Paragraph(title, self.styles["titel"]))
        self.elements.append(Paragraph(subtitle, self.styles["subtitel"]))

        # Spacer before the line
        self.elements.append(Spacer(1, 6))

        # Horizontal line across the page
        self.elements.append(
            HRFlowable(
                width="100%",
                thickness=2,
                color=PRIMARY_COLOR,
                spaceBefore=0,
                spaceAfter=12,
            )
        )

        self.elements.append(Spacer(1, 6))

    def header(self, data):
        table = Table(
            data,
            colWidths=[self.doc.width / 2, self.doc.width / 2],
        )

        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), _baseFontNameB),
                    ("TEXTCOLOR", (0, 0), (-1, 0), PRIMARY_COLOR),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 1), (1, -1), 0),
                    ("BOTTOMPADDING", (0, 1), (1, -1), 0),
                ]
            )
        )

        self.elements.append(table)
        self.elements.append(Spacer(1, 24))

    def data(self, df):
        nr_rows = df.shape[0]
        usage = df["usage"].sum()
        subtotal = df["total"].sum()

        # header row
        data = [["Datum", "Aantal", "Tarief", "Bedrag"]]

        # records
        for _, row in df.iterrows():
            data.append(
                [
                    row["date"].strftime("%Y-%m-%d"),
                    f"{row['usage']:.2f} kWh",
                    f"€ {row['cost']:.2f}",
                    f"€ {row['total']:.2f}",
                ]
            )

        # footer row
        data.extend([["Totaal", f"{usage:.2f} kWh", "", f"€ {subtotal:.2f}"]])

        table = Table(
            data,
            colWidths=[
                self.doc.width / 2,
                self.doc.width / 6,
                self.doc.width / 6,
                self.doc.width / 6,
            ],
        )

        table_style = [
            # all
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            # first row
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("TOPPADDING", (0, 0), (-1, 0), 7),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
            # last row
            ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
            ("FONT", (0, -1), (-1, -1), _baseFontNameB),
            ("TOPPADDING", (0, -1), (-1, -1), 7),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
            # column
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]

        # horizontal lines
        for row in range(1, nr_rows):
            table_style.append(
                ("LINEBELOW", (0, row), (-1, row), 0.5, ROW_DIVIDER_COLOR)
            )

        # thick footer line
        table_style.append(("LINEBELOW", (0, nr_rows), (-1, nr_rows), 1, PRIMARY_COLOR))

        table.setStyle(TableStyle(table_style))
        self.elements.append(table)
        self.elements.append(Spacer(1, 12))

    def summary(self, df):
        subtotal = df["total"].sum()
        vat = subtotal * VAT_RATE
        total = subtotal + vat

        data = [
            ["", "", "Subtotaal (excl. btw)", f"€ {subtotal:.2f}"],
            ["", "", f"BTW ({VAT_RATE * 100:.0f}%)", f"€ {vat:.2f}"],
            ["", "", "Totaal (incl. btw)", f"€ {total:.2f}"],
        ]

        table = Table(
            data,
            colWidths=[
                self.doc.width / 2,
                self.doc.width / 6,
                self.doc.width / 6,
                self.doc.width / 6,
            ],
        )

        table_style = [
            # last row
            ("LINEBELOW", (0, 1), (-1, 1), 1, PRIMARY_COLOR),
            ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
            ("FONT", (0, -1), (-1, -1), _baseFontNameB),
            ("FONTSIZE", (0, -1), (-1, -1), 12),
            ("TOPPADDING", (0, -1), (-1, -1), 7),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 7),
            # column
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ]

        table.setStyle(TableStyle(table_style))
        self.elements.append(table)
        self.elements.append(Spacer(1, 6))

    def build(self):
        self.doc.build(self.elements)

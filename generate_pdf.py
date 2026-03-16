"""
Passport Fee Schedule PDF Generator
Generates a PDF matching the Benton County Circuit Clerk fee schedule layout.
Reads fee data from fees.json and produces a professional PDF.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

FEES_FILE = Path(__file__).parent / "fees.json"
LOGO_FILE = Path(__file__).parent / "assets" / "benton_county_seal.png"
OUTPUT_FILE = Path(__file__).parent / "output" / "Fee-Schedule.pdf"

# Colors matching the PDF
HEADER_BLUE = (79, 129, 189)  # Blue used in table header rows
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


class FeeSchedulePDF(FPDF):
    """Custom PDF class for the Benton County fee schedule."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.set_auto_page_break(auto=True, margin=25)
        self.revision_date = datetime.now().strftime("%m/%Y")
        self.revision_year = datetime.now().strftime("%Y")

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        self.cell(
            0, 10,
            f"Benton County Circuit Clerk Revised Fee Schedule "
            f"{self.revision_year}({self.revision_date})",
            align="C",
        )

    def add_section_title(self, title):
        """Add an italic underlined section title like 'Passport Fees'."""
        self.set_font("Helvetica", "BI", 18)
        self.set_text_color(*BLACK)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        # Underline
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(6)

    def add_table_header(self, left_text, right_text="Fee"):
        """Add a blue header row for a fee table section."""
        self.set_fill_color(*HEADER_BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 10)

        col_width = self.w - self.l_margin - self.r_margin
        fee_col = 50
        desc_col = col_width - fee_col

        self.cell(desc_col, 7, "  " + left_text, border=1, fill=True)
        self.cell(fee_col, 7, right_text, border=1, fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*BLACK)

    def add_fee_row(self, description, fee_text, description2=None):
        """Add a fee row with description and fee amount."""
        self.set_font("Helvetica", "", 9)
        col_width = self.w - self.l_margin - self.r_margin
        fee_col = 50
        desc_col = col_width - fee_col

        x_start = self.get_x()
        y_start = self.get_y()

        # Calculate height needed for description
        # Use multi_cell to figure out height, then draw properly
        self.set_xy(x_start, y_start)

        full_desc = description
        if description2:
            full_desc = description + "\n" + description2

        # Calculate the height needed
        desc_lines = self.multi_cell(
            desc_col, 5, "  " + full_desc, border=0, align="L",
            new_x="RIGHT", new_y="TOP", dry_run=True, output="LINES"
        )
        row_height = max(len(desc_lines) * 5, 7)

        # Draw description cell
        self.set_xy(x_start, y_start)
        self.multi_cell(
            desc_col, row_height / len(desc_lines) if desc_lines else 7,
            "  " + full_desc, border="LBR", align="L",
            new_x="RIGHT", new_y="TOP",
        )

        # Draw fee cell
        self.set_xy(x_start + desc_col, y_start)
        self.cell(fee_col, row_height, fee_text, border="RB", align="R",
                  new_x="LMARGIN", new_y="NEXT")


def generate_passport_pdf(fees_data: dict, output_path: Path = None):
    """Generate the passport fee schedule PDF from fees data."""
    if output_path is None:
        output_path = OUTPUT_FILE

    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FeeSchedulePDF()

    # --- Page 1: Passport Info & Requirements ---
    pdf.add_page()

    # Header with logo (if available)
    if LOGO_FILE.exists():
        pdf.image(str(LOGO_FILE), x=15, y=12, w=30)
        pdf.set_xy(50, 15)
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 10, "Benton County Circuit Clerk & Recorder")
        pdf.set_xy(50, 27)
        pdf.set_font("Helvetica", "", 16)
        pdf.cell(0, 10, "Circuit Clerk - Brenda DeShields")
        pdf.ln(25)
    else:
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 10, "Benton County Circuit Clerk & Recorder",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 16)
        pdf.cell(0, 10, "Circuit Clerk - Brenda DeShields",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    pdf.add_section_title("Passport Fees")

    # Informational text
    pdf.set_font("Helvetica", "", 9)
    info_text = (
        "Fees described below apply to each applicant. "
    )
    pdf.multi_cell(0, 5, info_text, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.write(5, "Please Note: ")
    pdf.set_font("Helvetica", "", 9)
    pdf.write(
        5,
        "Passports issued to those 16 years and older are valid for ten years. "
        "Passports for children under 16 years are valid for five years and are "
        "not renewable. If you are behind in child support payments, you may not "
        "be able to obtain a passport. See Child Support. For assistance with "
        "special circumstances, visit the Recorder's Office or call 479-271-1017. "
        "Additional information may be found at the U.S. Department of State website."
    )
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0, 5,
        "Passport renewal applications may be completed if the applicant has "
        "previously had a U.S. Passport book/card issued within the past 15 years "
        "and issued when the applicant was 16 years or older. The undamaged U.S. "
        "Passport book/card should be submitted along with the DS-82 form and "
        "mailed to the U.S. Department of State by the applicant.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0, 5,
        "Please arrive no later than 3:40 p.m. at the Recorder's Office "
        "to process a passport application",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(3)

    # Passport Application Requirements
    pdf.set_font("Helvetica", "BU", 9)
    pdf.cell(0, 5, "Passport Application Requirements:",
             new_x="LMARGIN", new_y="NEXT")

    requirements = [
        'One (1) 2" by 2" Passport Photo',
        "U.S. Birth Certificate (original or certified copy) or naturalization papers",
        "Passport Application completed in black ink or typewritten",
        "Driver's license or a state-issued ID card",
        "For children ages birth to 15 years:",
        "For Children ages 16 and 17:",
    ]

    sub_items_5 = [
        "Both parents must sign the application in front of the accepting agent",
        "Child(ren) must be present at time of application",
    ]

    sub_items_6 = [
        "One parent must sign the application in front of the accepting agent",
        "Child(ren) must sign the application in front of the accepting agent",
    ]

    pdf.set_font("Helvetica", "", 9)
    for i, req in enumerate(requirements, 1):
        pdf.cell(0, 5, f"{i}. {req}", new_x="LMARGIN", new_y="NEXT")
        if i == 5:
            for sub in sub_items_5:
                pdf.cell(10)  # indent
                pdf.cell(0, 5, f"+   {sub}", new_x="LMARGIN", new_y="NEXT")
        elif i == 6:
            for sub in sub_items_6:
                pdf.cell(10)  # indent
                pdf.cell(0, 5, f"+   {sub}", new_x="LMARGIN", new_y="NEXT")

    # --- Page 2: Fee Tables ---
    pdf.add_page()

    fees = fees_data["fees"]
    delivery_times = fees_data.get("delivery_times", {})

    # Get delivery time strings
    express_time = delivery_times.get("usps_priority_express", {}).get(
        "timeframe", "1-2 Days"
    )

    # Adult Applicants
    pdf.add_table_header("ADULT APPLICANTS (Age 16 Years or Older)")

    app = fees["application"]["items"]
    pdf.add_fee_row("Adult Passport Book", f"${app['adult_book']['amount']:.2f}")
    pdf.add_fee_row(
        "Adult Passport Card (Not valid for international air travel.",
        f"${app['adult_card']['amount']:.2f}",
        "Valid only for travel by land and by sea to Canada, Mexico, Bermuda, "
        "and the Caribbean.)",
    )
    pdf.add_fee_row(
        "Adult Passport Book & Card", f"${app['adult_book_card']['amount']:.2f}"
    )

    pdf.ln(2)

    # Minor Applicants
    pdf.add_table_header("ALL MINOR APPLICANTS (Under the Age of 16)")

    pdf.add_fee_row("Minor Passport Book", f"${app['child_book']['amount']:.2f}")
    pdf.add_fee_row(
        "Minor Passport Card (Not valid for international air travel.",
        f"${app['child_card']['amount']:.2f}",
        "Valid only for travel by land and by sea to Canada, Mexico, Bermuda, "
        "and the Caribbean.)",
    )
    pdf.add_fee_row(
        "Minor Passport Book & Card",
        f"${app['child_book_card']['amount']:.2f}",
    )

    pdf.ln(2)

    # Additional Fees
    pdf.add_table_header("Additional Fees")

    exe = fees["execution"]["items"]
    ship = fees["shipping"]["items"]

    pdf.add_fee_row(
        "Execution Fee per applicant Adult & Minor",
        f"${exe['execution_fee']['amount']:.2f}",
        "(payable to Benton County Circuit Clerk's Office)",
    )
    pdf.add_fee_row("Passport Photos", f"${exe['photo']['amount']:.2f}")

    express_delivery = ship["priority_express"].get("delivery_time", express_time)
    pdf.add_fee_row(
        f"Priority Mail Expense - Overnight up to {express_delivery} Guarantee "
        f"(US Mail Service not guaranteed by the Circuit Clerk's Office). "
        f"Payable to the United States Postal Service.",
        f"${ship['priority_express']['amount']:.2f}",
        "*USPS rates may change*",
    )
    pdf.add_fee_row(
        f"{ship['priority_1_3_day'].get('delivery_time', '1-3 Days')} Return "
        f"Services US Postal Priority Mail Overnight up to {express_delivery} "
        f"Guarantee service.",
        f"${ship['priority_1_3_day']['amount']:.2f}",
        "(USPS Express Mail\u00ae Service)",
    )
    pdf.add_fee_row(
        "Expedite Fee (payable to the U.S. Department of State)",
        f"${ship['expedite']['amount']:.2f}",
    )

    pdf.ln(5)

    # Return delivery note
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(
        0, 4,
        "Return Deliver: 1-3 day delivery service you will include the delivery "
        "fee with your passport fee in your check or money order payable to the "
        "US Department of State for faster return shipping. You may receive your "
        "passport and your supporting documents submitted with your application "
        "in separate mailings. (The Circuit Clerk does not offer a guarantee for "
        "US Postal Services)",
        new_x="LMARGIN", new_y="NEXT",
    )

    pdf.ln(8)

    # Contact info
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Contact", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)

    contacts = [
        ("Brenda DeShields", "Circuit Clerk & Recorder", "(479) 271-1015",
         "brenda.deshields@bentoncountyar.gov"),
        ("Villi Mercado", "Recorder Administrator", "(479) 271-1017",
         "villi.mercado@bentoncountyar.gov"),
        ("Brittany Cadell", "Courts Administrator", "(479) 271-1015",
         "brittany.cadell@bentoncountyar.gov"),
    ]

    for name, title, phone, email in contacts:
        pdf.cell(0, 5, f"{name}-{title} {phone}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 200)
        pdf.cell(0, 5, email, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*BLACK)
        pdf.ln(2)

    # Save
    pdf.output(str(output_path))
    return output_path


def main():
    with open(FEES_FILE) as f:
        fees_data = json.load(f)

    output = OUTPUT_FILE
    if len(sys.argv) > 1:
        output = Path(sys.argv[1])

    path = generate_passport_pdf(fees_data, output)
    print(f"PDF generated: {path}")


if __name__ == "__main__":
    main()

"""
Passport Fee Schedule PDF Generator
Generates a PDF matching the Benton County Circuit Clerk fee schedule layout.
Reads fee data from fees.json and produces a professional 4-page PDF.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from fpdf import FPDF

FEES_FILE = Path(__file__).parent / "fees.json"
LOGO_FILE = Path(__file__).parent / "docs" / "Benton County Logo Clear Background.png"
OUTPUT_FILE = Path(__file__).parent / "output" / "Fee-Schedule.pdf"

# Colors
HEADER_BLUE = (79, 129, 189)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LINK_BLUE = (0, 0, 200)
NAVY = (22, 54, 92)
LIGHT_BLUE_BG = (218, 232, 245)


class FeeSchedulePDF(FPDF):
    """Custom PDF class for the Benton County fee schedule."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.set_margins(left=18, top=10, right=18)
        self.set_auto_page_break(auto=True, margin=20)
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

    def add_header_with_logo(self):
        """Add the header with county seal and title."""
        self.set_text_color(*NAVY)
        text_x = self.l_margin
        if LOGO_FILE.exists():
            # Logo has ~6.35mm (0.25") of transparent padding on the left
            self.image(str(LOGO_FILE), x=-6.35, y=8, w=74)
            text_x = self.l_margin + 35
            self.set_xy(text_x, 22)
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 8, "Benton County Circuit Clerk & Recorder",
                  new_x="LMARGIN", new_y="NEXT")
        if LOGO_FILE.exists():
            self.set_xy(text_x, 30)
        self.set_font("Helvetica", "", 14)
        self.cell(0, 8, "Circuit Clerk - Brenda DeShields",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*BLACK)
        if LOGO_FILE.exists():
            self.ln(10)
        else:
            self.ln(5)

    def add_section_title(self, title):
        """Add an italic underlined section title."""
        self.set_font("Helvetica", "BI", 18)
        self.set_text_color(*NAVY)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        y = self.get_y()
        self.set_draw_color(*NAVY)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_draw_color(*BLACK)
        self.set_text_color(*BLACK)
        self.ln(6)

    def add_table_header(self, left_text, right_text="Fee", fee_col=50):
        """Add a blue header row for a fee table section."""
        self.set_fill_color(*HEADER_BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 10)

        col_width = self.w - self.l_margin - self.r_margin
        desc_col = col_width - fee_col

        self.cell(desc_col, 7, " " + left_text, border=1, fill=True)
        self.cell(fee_col, 7, right_text, border=1, fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*BLACK)

    def add_fee_row(self, description, fee_text, description2=None, fee_col=50):
        """Add a fee row with description and fee amount."""
        self.set_font("Helvetica", "", 9)
        col_width = self.w - self.l_margin - self.r_margin
        desc_col = col_width - fee_col
        padding = 2  # left padding inside description cell
        line_h = 5

        x_start = self.get_x()
        y_start = self.get_y()

        full_desc = description
        if description2:
            full_desc = description + "\n" + description2

        # Calculate the height needed for both columns
        desc_lines = self.multi_cell(
            desc_col - padding, line_h, full_desc, border=0, align="L",
            new_x="RIGHT", new_y="TOP", dry_run=True, output="LINES"
        )
        fee_lines = self.multi_cell(
            fee_col - padding, line_h, fee_text, border=0, align="R",
            new_x="RIGHT", new_y="TOP", dry_run=True, output="LINES"
        )
        row_height = max(len(desc_lines) * line_h, len(fee_lines) * line_h, 10)

        desc_text_h = len(desc_lines) * line_h
        fee_text_h = len(fee_lines) * line_h
        desc_offset = (row_height - desc_text_h) / 2
        fee_offset = (row_height - fee_text_h) / 2

        # Draw description cell border
        self.set_xy(x_start, y_start)
        self.cell(desc_col, row_height, "", border="LBR")

        # Draw description text with padding, vertically centered
        self.set_xy(x_start + padding, y_start + desc_offset)
        self.multi_cell(
            desc_col - padding, line_h,
            full_desc, border=0, align="L",
            new_x="RIGHT", new_y="TOP",
        )

        # Draw fee cell border
        self.set_xy(x_start + desc_col, y_start)
        self.cell(fee_col, row_height, "", border="RB")

        # Draw fee text vertically centered
        self.set_xy(x_start + desc_col, y_start + fee_offset)
        self.multi_cell(
            fee_col - padding, line_h,
            fee_text, border=0, align="R",
            new_x="LMARGIN", new_y="TOP",
        )

        # Move to next row
        self.set_xy(x_start, y_start + row_height)

    def add_requirements_table(self, title, items):
        """Add a requirements section with background color, title and numbered items."""
        # Calculate total height for background
        total_lines = 1 + len(items)  # title + items
        block_h = total_lines * 5 + 2  # small padding
        x_start = self.get_x()
        y_start = self.get_y()

        # Draw background rectangle
        self.set_fill_color(*LIGHT_BLUE_BG)
        full_w = self.w - self.l_margin - self.r_margin
        self.rect(x_start, y_start, full_w, block_h, "F")

        # Draw title and items on top of background
        self.set_xy(x_start + 2, y_start + 1)
        self.set_font("Helvetica", "BU", 9)
        self.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        for i, item in enumerate(items, 1):
            self.set_x(x_start + 2)
            self.cell(0, 5, f"{i}. {item}", new_x="LMARGIN", new_y="NEXT")


def generate_passport_pdf(fees_data: dict, output_path: Path = None):
    """Generate the full fee schedule PDF from fees data."""
    if output_path is None:
        output_path = OUTPUT_FILE

    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FeeSchedulePDF()

    # ===== PAGE 1: Filing Fees =====
    pdf.add_page()
    pdf.add_header_with_logo()
    pdf.add_section_title("Filing Fees")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Court Fees / Recorder's Fees / Passport Fees",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0, 5,
        "The Office of the Circuit Clerk accepts the following forms of payment: cash, personal "
        "checks, business checks, cashier's checks, postal money orders, and non-postal money orders.",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(5)

    # Court Filing Fees table
    pdf.add_table_header("Court Filing", "Fees", fee_col=28)

    court_fees = [
        ("Initiating a cause of action in the Circuit Court:\n"
         "(Civil, domestic, out-of-state judgments, and all appeal(s) Ark Code Ann. \u00a721-6-403(b)(1)",
         "$165.00"),
        ("Reopening a cause of action in the Circuit Court Ark Code Ann. \u00a721-6-403(b)(2)",
         "$50.00"),
        ("Out-of-state subpoena", "$2.50"),
        ("Any cause of action which by court order is transferred from any district or\n"
         "circuit to a circuit court",
         "$50.00"),
        ("Initiating a criminal cause of action being appealed to the Circuit Court\n"
         "Ark Code Ann. \u00a721-6-403(b)(1)",
         "$150.00"),
        ("Scire Facias: a Writ for a dormant judgment against a person to be revived",
         "$20.00"),
        ("Writs of Garnishment, Writs of Execution, and Writs of Possession",
         "$20.00"),
        ("Circuit Clerk issuing subpoenas for civil and domestic cases\n"
         "(When counsel requests for the clerk to prepare)",
         "$2.50"),
        ("Circuit Clerk issuing summons for civil and domestic cases", "$2.50"),
        ("Filing a pleading by fax", "$1.00 (per page)"),
        ("Copy of a pleading or any document", "$0.25 (per page)"),
        ("Certification of a Court Document", "$5.00"),
        ("Authentication of a Court document or Court record", "$5.00"),
        ("Filing an appointment to serve as a Civil Process Server", "*$140.00"),
        ("Renewal of a Civil Process Server", "*$50.00"),
        ("Once approved by the Court, a Process Server Badge Fee will apply of", "$5.00"),
    ]

    for desc, fee in court_fees:
        pdf.add_fee_row(desc, fee, fee_col=28)

    # ===== PAGE 2: Recorder's Fees =====
    pdf.add_page()
    pdf.add_section_title("Recorder's Fees")

    pdf.add_table_header("Recorder's Filings", "Fees")

    recorder_fees = [
        ("Deeds, Deeds of Trust, Mortgages, Release Deeds, Powers Of Attorney, Plats, "
         "Survey Plats, Notary Bonds, Foreign Judgments (within the State of Arkansas), "
         "Lis-Pendens, Medical Liens, Mechanic's and Materialman's Liens, Federal Tax Liens, "
         "and any Recordable instruments except as otherwise described in this section\n"
         "Ark. Code Ann. \u00a721-6-306.",
         "$15.00\nPlus $5.00 for every page\nsubsequent to the first\n"
         "Note: a two-sided instrument\ncounts as two pages"),
        ("Mortgage Assignments, Mortgage Releases, and other instruments\n"
         "Ark Code Ann. \u00a721-6-306",
         "If a single document lists\nmultiple instruments:\n"
         "No fee for the first instrument.\nThereafter, a fee of $15.00 per\n"
         "additional instrument listed,\nnot to exceed $300.00"),
        ("Mortgage's or Trustee's Notice of Default and Intention to Sell\n"
         "(Ark Code Ann. \u00a718-50-104) Ark Fee Code \u00a721-6-306",
         "$140.00\nPlus recording fee of $15.00 for\n"
         "the first page (1) side only and\n$5.00 for each additional page"),
        ("Waiver of Recordable Instrument requirements of Ark. Code Ann. \u00a714-15-402(b)(1) for\n"
         "good cause (at Recorder's discretion) Ark. Code Ann. \u00a721-6-306.",
         "$25.00"),
        ("State Tax Liens", "$8.00"),
        ("Financing Statement/UCC Filings, Pursuant to Act 942 of 2009, the filing of all\n"
         "agricultural liens and farm-related security interests will be made in the Arkansas\n"
         "Secretary of State's Office", ""),
        ("UCC Filings - Fixture Filings", "$12.00"),
        ("Termination Statement Certification", "$6.00"),
        ("Certificate of Assessment of any other instrument not specified", "$8.00"),
        ("Certified copy of a Recorded document",
         "$5.00 for the first page\n$0.25 per subsequent page"),
        ("Copy of a document", "$0.25 (per page)"),
        ("Certificate of Proof of Notary", "$5.00"),
        ("Copies of full-size plats", "$3.00 (per page)"),
        ("DD2-14 forms", "No Charge"),
        ("Bond in Contest", "$15.00\nPlus $5.00 for each\nadditional page"),
    ]

    for desc, fee in recorder_fees:
        pdf.add_fee_row(desc, fee)

    # ===== PAGE 3: Recorded Instrument Requirements + Passport Info =====
    pdf.add_page()
    pdf.add_section_title("Recorded Instrument Requirements")

    # Recordable Instrument Requirements table
    pdf.add_requirements_table("Recordable Instrument Requirements:", [
        "Original instrument",
        "Notarized signature",
        "Tax statement return address on document",
        "Name of instrument preparer",
        "Revenue stamps on warranty deeds (if revenue changed hands)",
        "\"I Certify\" statement on all warranty deeds (and any deed that has revenue stamps affixed)",
        "A self-addressed stamped envelope (if sending in by mail)",
        "Compliance with Standardized Form Act 757 of 2003 (Or refer to Ark. Code Ann. \u00a7 14-15-402)",
    ])
    pdf.ln(5)

    # Surveys and Plats Requirements
    pdf.add_requirements_table("Surveys and Plats Requirements:", [
        "Original instrument",
        "All Required signatures on each instrument-including City Planning, if applicable.",
        "Accompanied with a reduced copy, if larger than 18\" by 24\".",
        "Plat Affidavit of Compliance - For copy of form go to LAND RECORDS also in ONLINE FORMS.",
        "Color plats accepted ONLY if accompanied with a black and white copy.",
    ])
    pdf.ln(8)

    # Passport Fees section
    pdf.add_section_title("Passport Fees")

    pdf.set_font("Helvetica", "", 9)
    info_text = "Fees described below apply to each applicant. "
    pdf.multi_cell(0, 5, info_text, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.write(5, "Please Note: ")
    pdf.set_font("Helvetica", "", 9)
    pdf.write(
        5,
        "Passports issued to those 16 years and older are valid for ten years. "
        "Passports for children under 16 years are valid for five years and are "
        "not renewable. If you are behind in child support payments, you may not "
        "be able to obtain a passport. See "
    )
    pdf.set_font("Helvetica", "U", 9)
    pdf.set_text_color(*LINK_BLUE)
    pdf.write(5, "Child Support")
    pdf.set_text_color(*BLACK)
    pdf.set_font("Helvetica", "", 9)
    pdf.write(
        5,
        ". For assistance with special circumstances, visit the Recorder's Office "
        "or call 479-271-1017. Additional information may be found at the "
    )
    pdf.set_font("Helvetica", "U", 9)
    pdf.set_text_color(*LINK_BLUE)
    pdf.write(5, "U.S. Department of State website")
    pdf.set_text_color(*BLACK)
    pdf.set_font("Helvetica", "", 9)
    pdf.write(5, ".")
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

    # Passport Application Requirements with background
    req_lines = 6 + 2 + 2  # 6 requirements + 2 sub-items each
    block_h = (1 + req_lines) * 5 + 2
    x_start = pdf.get_x()
    y_start = pdf.get_y()
    full_w = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_fill_color(*LIGHT_BLUE_BG)
    pdf.rect(x_start, y_start, full_w, block_h, "F")

    pdf.set_xy(x_start + 2, y_start + 1)
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
        pdf.set_x(x_start + 2)
        pdf.cell(0, 5, f"{i}. {req}", new_x="LMARGIN", new_y="NEXT")
        if i == 5:
            for sub in sub_items_5:
                pdf.set_x(x_start + 12)
                pdf.cell(0, 5, f"+   {sub}", new_x="LMARGIN", new_y="NEXT")
        elif i == 6:
            for sub in sub_items_6:
                pdf.set_x(x_start + 12)
                pdf.cell(0, 5, f"+   {sub}", new_x="LMARGIN", new_y="NEXT")

    # ===== PAGE 4: Fee Tables + Contact =====
    pdf.add_page()

    fees = fees_data["fees"]
    delivery_times = fees_data.get("delivery_times", {})

    # Get delivery time strings
    express_time = delivery_times.get("usps_priority_express", {}).get(
        "timeframe", "1-2 Days"
    )
    # Extract just the max number for "up to X-Day Guarantee" wording
    # e.g. "1-2 Days" -> "2-Day", "1-3 Days" -> "3-Day"
    express_max = express_time.split("-")[-1].replace(" Days", "").replace(" Day", "").strip()
    express_guarantee = f"{express_max}-Day"

    return_time = fees_data["fees"]["shipping"]["items"]["return_delivery"].get(
        "delivery_time", "1-3 Days"
    )
    return_range = return_time.replace(" Days", "").replace(" Day", "").strip()
    return_max = return_time.split("-")[-1].replace(" Days", "").replace(" Day", "").strip()
    return_guarantee = f"{return_max}-Day"

    # Adult Applicants
    pdf.add_table_header("ADULT APPLICANTS (Age 16 Years or Older)", fee_col=28)

    app = fees["application"]["items"]
    pdf.add_fee_row("Adult Passport Book", f"${app['adult_book']['amount']:.2f}", fee_col=28)
    pdf.add_fee_row(
        "Adult Passport Card (Not valid for international air travel.",
        f"${app['adult_card']['amount']:.2f}",
        "Valid only for travel by land and by sea to Canada, Mexico, Bermuda, "
        "and the Caribbean.)",
        fee_col=28,
    )
    pdf.add_fee_row(
        "Adult Passport Book & Card", f"${app['adult_book_card']['amount']:.2f}", fee_col=28
    )

    pdf.ln(2)

    # Minor Applicants
    pdf.add_table_header("ALL MINOR APPLICANTS (Under the Age of 16)", fee_col=28)

    pdf.add_fee_row("Minor Passport Book", f"${app['child_book']['amount']:.2f}", fee_col=28)
    pdf.add_fee_row(
        "Minor Passport Card (Not valid for international air travel.",
        f"${app['child_card']['amount']:.2f}",
        "Valid only for travel by land and by sea to Canada, Mexico, Bermuda, "
        "and the Caribbean.)",
        fee_col=28,
    )
    pdf.add_fee_row(
        "Minor Passport Book & Card",
        f"${app['child_book_card']['amount']:.2f}",
        fee_col=28,
    )

    pdf.ln(2)

    # Additional Fees
    pdf.add_table_header("Additional Fees", fee_col=28)

    exe = fees["execution"]["items"]
    ship = fees["shipping"]["items"]

    pdf.add_fee_row(
        "Execution Fee per applicant Adult & Minor",
        f"${exe['execution_fee']['amount']:.2f}",
        "(payable to Benton County Circuit Clerk's Office)",
        fee_col=28,
    )
    pdf.add_fee_row("Passport Photos", f"${exe['photo']['amount']:.2f}", fee_col=28)

    pdf.add_fee_row(
        f"Priority Mail Express - Overnight up to {express_guarantee} Guarantee "
        f"(US Mail Service not guaranteed by the Circuit Clerk's "
        f"Office). Payable to the United States Postal Service.",
        f"${ship['priority_express']['amount']:.2f}",
        "*USPS rates may change*",
        fee_col=28,
    )
    pdf.add_fee_row(
        f"{return_range} Day Return Services US Postal Priority Mail Overnight "
        f"up to {return_guarantee} Guarantee service.",
        f"${ship['return_delivery']['amount']:.2f}",
        "(USPS Express Mail\u00ae Service)",
        fee_col=28,
    )
    pdf.add_fee_row(
        "Expedite Fee (payable to the U.S. Department of State)",
        f"${ship['expedite']['amount']:.2f}",
        fee_col=28,
    )

    pdf.ln(5)

    # Return delivery note
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(
        0, 4,
        f"Return Deliver: {return_range} day delivery service you will include the delivery "
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
        pdf.set_text_color(*LINK_BLUE)
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

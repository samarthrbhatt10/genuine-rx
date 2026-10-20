"""
pdf_report.py — Generates a printable PDF savings report for a patient.

Uses fpdf2 (pure Python, no wkhtmltopdf needed).
The report shows:
  - Patient's name / user phone
  - Current date
  - Each tracked medicine with its branded price vs Jan Aushadhi price
  - Total savings in ₹ per month (estimated)
  - Government PMBJP branding footer

Usage:
    from api.pdf_report import generate_savings_pdf
    path = generate_savings_pdf(user_id=1, conn=conn)
    # returns path to a temp PDF file
"""
import os
import tempfile
from datetime import datetime
from decimal import Decimal

from fpdf import FPDF


# Colour palette
TEAL    = (0, 128, 128)
DARK    = (15, 23, 42)
WHITE   = (255, 255, 255)
LIGHT   = (241, 245, 249)
GREEN   = (22, 163, 74)
RED     = (220, 38, 38)
GRAY    = (100, 116, 139)


class SavingsReportPDF(FPDF):
    def header(self):
        self.set_fill_color(*TEAL)
        self.rect(0, 0, 210, 28, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 18)
        self.set_xy(10, 6)
        self.cell(0, 10, "GenuineRX - Medicine Savings Report", ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_xy(10, 17)
        self.cell(0, 6, "Powered by PMBJP Jan Aushadhi Price List  |  Government of India", ln=False)
        self.ln(30)

    def footer(self):
        self.set_y(-18)
        self.set_draw_color(*TEAL)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.set_xy(10, self.get_y() + 2)
        self.cell(
            0, 6,
            "This report is for informational purposes only. "
            "Always consult a licensed pharmacist before switching medicines.",
            align="C"
        )


def generate_savings_pdf(
    medicines: list[dict],
    user_phone: str = "Patient",
    output_path: str | None = None,
) -> str:
    """
    Generate a PDF savings report.

    Args:
        medicines: List of tracked medicine dicts with keys:
                   brand_name, profile_label, latest_price,
                   ja_price, savings_rupees, savings_percent
        user_phone: Phone or name label for the patient.
        output_path: Optional file path. A temp file is created if None.

    Returns:
        Absolute path to the generated PDF file.
    """
    pdf = SavingsReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Meta section ─────────────────────────────────────────────────────────
    date_str = datetime.now().strftime("%d %B %Y, %I:%M %p")
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*DARK)
    pdf.cell(90, 7, f"Patient:  {user_phone}", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 7, f"Generated: {date_str}", ln=True, align="R")
    pdf.set_text_color(*DARK)
    pdf.ln(3)

    # ── Section heading ───────────────────────────────────────────────────────
    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*DARK)
    pdf.set_x(10)
    pdf.cell(190, 8, "  Tracked Medicines & Savings Breakdown", ln=True, fill=True)
    pdf.ln(2)

    # ── Table header ──────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*TEAL)
    pdf.set_text_color(*WHITE)
    pdf.set_x(10)
    pdf.cell(38, 7, "For",            fill=True, border=0)
    pdf.cell(50, 7, "Brand Name",     fill=True, border=0)
    pdf.cell(30, 7, "Brand (Rs.)",    fill=True, border=0, align="R")
    pdf.cell(35, 7, "Jan Aushadhi",   fill=True, border=0, align="R")
    pdf.cell(30, 7, "You Save",       fill=True, border=0, align="R")
    pdf.ln()

    # ── Table rows ────────────────────────────────────────────────────────────
    total_savings = 0.0
    fill = False
    for med in medicines:
        fill = not fill
        pdf.set_fill_color(*(LIGHT if fill else WHITE))
        pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(10)

        brand_price = med.get("latest_price") or 0
        ja_price    = med.get("ja_price")
        savings_rs  = med.get("savings_rupees") or 0
        savings_pct = med.get("savings_percent") or 0
        total_savings += float(savings_rs)

        pdf.cell(38, 7, str(med.get("profile_label", "self")), fill=True)
        pdf.cell(50, 7, str(med.get("brand_name", "")),        fill=True)
        pdf.cell(30, 7, f"Rs.{brand_price:.2f}",               fill=True, align="R")

        if ja_price is not None:
            pdf.set_text_color(*GREEN)
            pdf.cell(35, 7, f"Rs.{float(ja_price):.2f}", fill=True, align="R")
        else:
            pdf.set_text_color(*GRAY)
            pdf.cell(35, 7, "N/A", fill=True, align="R")

        pdf.set_text_color(*(GREEN if savings_rs > 0 else GRAY))
        pdf.cell(30, 7, f"Rs.{savings_rs:.2f} ({savings_pct:.0f}%)", fill=True, align="R")
        pdf.set_text_color(*DARK)
        pdf.ln()

    # ── Total savings highlight box ───────────────────────────────────────────
    pdf.ln(4)
    pdf.set_fill_color(*GREEN)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_x(10)
    pdf.cell(
        190, 12,
        f"  TOTAL ESTIMATED MONTHLY SAVINGS:   Rs.{total_savings:.2f}",
        fill=True, ln=True, align="L"
    )

    # ── Where to buy section ──────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_x(10)
    pdf.cell(0, 7, "Where to Get Jan Aushadhi Medicines:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY)
    tips = [
        "1. Visit your nearest Jan Aushadhi Kendra (search on UMANG app or pmbjp.gov.in)",
        "2. Show this report to the pharmacist - all medicines are WHO-approved generics",
        "3. PMBJP helpline: 1800-11-8111 (toll-free) for nearest store location",
        "4. Download UMANG app > search 'Jan Aushadhi Sugam' for live price lookup",
    ]
    for tip in tips:
        pdf.set_x(10)
        pdf.cell(0, 6, tip, ln=True)

    # ── Write file ────────────────────────────────────────────────────────────
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="genuinerx_report_")
        os.close(fd)

    pdf.output(output_path)
    return output_path


"""Generate Emergency Recovery Sheet PDF for secure password storage."""
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_recovery_sheet_pdf(
    password: str,
    backup_location: str,
    output_path: Path,
    sheet_type: str = "backup",
) -> bool:
    """
    Generate an Emergency Recovery Sheet PDF.

    Args:
        password: The 16+ character passphrase
        backup_location: Where backups are stored (e.g., "Chiavetta USB in cassaforte")
        output_path: Where to save the PDF
        sheet_type: "backup" or "keys" to customize the sheet

    Returns:
        True if successful, False otherwise
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#c62828"),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        title_text = (
            "🔐 SCHEDA DI RECUPERO CRITICA"
            if sheet_type == "backup"
            else "🔑 SCHEDA DI RECUPERO CHIAVI"
        )
        elements.append(Paragraph(title_text, title_style))

        # Warning box
        warning_style = ParagraphStyle(
            "Warning",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#b71c1c"),
            spaceAfter=12,
            leftIndent=10,
            rightIndent=10,
        )

        warning_text = (
            "⚠️ ATTENZIONE CRITICA: Conservare questo foglio in cassaforte o in luogo sicuro.\n"
            "Senza questa password, il database cifrato è IRRECUPERABILE per sempre."
        )
        elements.append(Paragraph(warning_text, warning_style))
        elements.append(Spacer(1, 0.5 * cm))

        # Document info table
        info_data = [
            ["Tipo Scheda:", "Recupero Password" if sheet_type == "backup" else "Recupero Chiavi"],
            ["Data Creazione:", datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
            [
                "Applicativo:",
                "AbbonaMunicipale - Città di Scalea",
            ],
        ]

        info_table = Table(info_data, colWidths=[4 * cm, 11 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 0.7 * cm))

        # Password section
        pwd_title = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#c62828"),
            spaceAfter=10,
            fontName="Helvetica-Bold",
        )
        elements.append(Paragraph("PASSWORD (Minimo 16 Caratteri)", pwd_title))

        # Large password box
        pwd_table = Table(
            [[password]],
            colWidths=[13 * cm],
        )
        pwd_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fff8e1")),
                    ("BORDER", (0, 0), (0, 0), 2, colors.HexColor("#c62828")),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (0, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 12),
                    ("LEFTPADDING", (0, 0), (0, 0), 12),
                    ("RIGHTPADDING", (0, 0), (0, 0), 12),
                    ("FONTNAME", (0, 0), (0, 0), "Courier-Bold"),
                    ("FONTSIZE", (0, 0), (0, 0), 13),
                ]
            )
        )
        elements.append(pwd_table)
        elements.append(Spacer(1, 0.7 * cm))

        # Backup location section
        elements.append(Paragraph("UBICAZIONE BACKUP", pwd_title))
        location_style = ParagraphStyle(
            "Location",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=10,
            leftIndent=10,
        )
        elements.append(Paragraph(backup_location, location_style))
        elements.append(Spacer(1, 0.7 * cm))

        # Instructions
        instr_title = Paragraph("ISTRUZIONI DI SICUREZZA", pwd_title)
        elements.append(instr_title)

        instructions = [
            "1. Stampa questo foglio o conservalo in formato digitale sicuro",
            "2. Rimuovi il foglio dalla stampante immediatamente",
            "3. Conserva questo foglio in cassaforte, separato dal computer",
            "4. Annota la data di creazione in un registro offline",
            "5. Se il foglio viene smarrito, genera una nuova Scheda di Recupero",
            "6. NON inviare via email, SMS o cloud",
            "7. NON fotografare con dispositivi connessi ad internet",
        ]

        for instruction in instructions:
            instr_style = ParagraphStyle(
                "Instruction",
                parent=styles["Normal"],
                fontSize=9,
                spaceAfter=6,
                leftIndent=20,
            )
            elements.append(Paragraph(instruction, instr_style))

        elements.append(Spacer(1, 0.7 * cm))

        # Final warning
        final_warning_style = ParagraphStyle(
            "FinalWarning",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#b71c1c"),
            spaceAfter=0,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        final_text = (
            "🔴 SENZA QUESTA PASSWORD, I DATI SONO PERSI PER SEMPRE\n"
            "Conservare questo foglio con la massima cura."
        )
        elements.append(Paragraph(final_text, final_warning_style))

        # Build PDF
        doc.build(elements)
        return True

    except Exception as e:
        print(f"Errore generazione scheda recupero: {e}")
        return False

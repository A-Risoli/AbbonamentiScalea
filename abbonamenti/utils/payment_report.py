"""Generate Payment Report PDF with subscription and revenue statistics."""
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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


def generate_payment_report_pdf(
    output_path: Path,
    period_type: str,
    period_label: str,
    stats: dict,
    pos_revenue: float,
    bollettino_revenue: float,
) -> bool:
    """
    Generate a Payment Report PDF with aggregated statistics.

    Args:
        output_path: Where to save the PDF
        period_type: Type of period ("Giorno", "Settimana", "Mese", "Anno")
        period_label: Human-readable period label (e.g., "Gennaio 2026", "31/01/2026")
        stats: Dictionary with payment statistics from get_payment_statistics()
        pos_revenue: Total revenue from POS payments
        bollettino_revenue: Total revenue from BOLLETTINO payments

    Returns:
        True if successful, False otherwise
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=colors.HexColor("#1976d2"),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
        elements.append(Paragraph("Report Abbonamenti e Incassi", title_style))

        # Subtitle with period
        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=14,
            textColor=colors.HexColor("#757575"),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName="Helvetica",
        )
        elements.append(
            Paragraph(f"{period_type}: {period_label}", subtitle_style)
        )

        # Generation timestamp
        timestamp_style = ParagraphStyle(
            "Timestamp",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#9e9e9e"),
            spaceAfter=20,
            alignment=TA_RIGHT,
        )
        elements.append(
            Paragraph(
                f"Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}",
                timestamp_style,
            )
        )

        elements.append(Spacer(1, 0.5 * cm))

        # Check if there's data
        if stats["subscription_count"] == 0:
            # No data message
            no_data_style = ParagraphStyle(
                "NoData",
                parent=styles["Normal"],
                fontSize=14,
                textColor=colors.HexColor("#d32f2f"),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )
            elements.append(
                Paragraph(
                    "⚠️ Nessun dato disponibile per il periodo selezionato",
                    no_data_style,
                )
            )
        else:
            # Summary statistics section
            summary_title_style = ParagraphStyle(
                "SectionTitle",
                parent=styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#1976d2"),
                spaceAfter=12,
                spaceBefore=10,
                fontName="Helvetica-Bold",
            )
            elements.append(Paragraph("📊 Riepilogo Generale", summary_title_style))

            # Summary table
            summary_data = [
                ["Indicatore", "Valore"],
                [
                    "Totale Incassi",
                    f"{stats['total_revenue']:.2f} €",
                ],
                [
                    "Numero Abbonamenti",
                    str(stats["subscription_count"]),
                ],
                [
                    "Incasso Medio",
                    f"{stats['average_payment']:.2f} €",
                ],
            ]

            summary_table = Table(summary_data, colWidths=[8 * cm, 7 * cm])
            summary_table.setStyle(
                TableStyle(
                    [
                        # Header row
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        # Data rows
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#424242")),
                        ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor("#1976d2")),
                        ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
                        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 1), (-1, -1), 11),
                        ("ALIGN", (0, 1), (0, -1), "LEFT"),
                        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                        # Borders
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e0e0e0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ]
                )
            )
            elements.append(summary_table)

            elements.append(Spacer(1, 0.8 * cm))

            # Payment methods breakdown section
            elements.append(
                Paragraph("💳 Dettaglio Metodi di Pagamento", summary_title_style)
            )

            # Payment methods table
            payment_data = [
                ["Metodo di Pagamento", "N° Abbonamenti", "Incasso Totale"],
                [
                    "POS (Carta)",
                    str(stats["pos_count"]),
                    f"{pos_revenue:.2f} €",
                ],
                [
                    "Bollettino Postale",
                    str(stats["bollettino_count"]),
                    f"{bollettino_revenue:.2f} €",
                ],
                [
                    "TOTALE",
                    str(stats["subscription_count"]),
                    f"{stats['total_revenue']:.2f} €",
                ],
            ]

            payment_table = Table(payment_data, colWidths=[7 * cm, 4 * cm, 4 * cm])
            payment_table.setStyle(
                TableStyle(
                    [
                        # Header row
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("ALIGN", (0, 0), (0, 0), "LEFT"),
                        ("ALIGN", (1, 0), (-1, 0), "CENTER"),
                        # Data rows (POS and Bollettino)
                        ("BACKGROUND", (0, 1), (-1, 2), colors.white),
                        ("TEXTCOLOR", (0, 1), (-1, 2), colors.HexColor("#424242")),
                        ("FONTNAME", (0, 1), (-1, 2), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, 2), 10),
                        ("ALIGN", (0, 1), (0, 2), "LEFT"),
                        ("ALIGN", (1, 1), (-1, 2), "CENTER"),
                        # Total row
                        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e3f2fd")),
                        ("TEXTCOLOR", (0, 3), (-1, 3), colors.HexColor("#1976d2")),
                        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 3), (-1, 3), 11),
                        ("ALIGN", (0, 3), (0, 3), "LEFT"),
                        ("ALIGN", (1, 3), (-1, 3), "CENTER"),
                        # Borders
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e0e0e0")),
                        ("LINEABOVE", (0, 3), (-1, 3), 2, colors.HexColor("#1976d2")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ]
                )
            )
            elements.append(payment_table)

            elements.append(Spacer(1, 1 * cm))

            # Footer note
            footer_style = ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#757575"),
                alignment=TA_CENTER,
            )
            elements.append(
                Paragraph(
                    "AbbonaMunicipale - Città di Scalea | Report generato automaticamente",
                    footer_style,
                )
            )

        # Build PDF
        doc.build(elements)
        return True

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return False

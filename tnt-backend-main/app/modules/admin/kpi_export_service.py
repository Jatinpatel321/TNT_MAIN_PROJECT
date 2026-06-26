import io
import pandas as pd
from datetime import datetime
from typing import Any, Dict

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_kpi_excel(kpis: Dict[str, Any]) -> io.BytesIO:
    """Generate multi-sheet Excel report of KPIs using pandas and openpyxl."""
    output = io.BytesIO()

    # Sheet 1: General Overview
    overview_data = {
        "KPI Category": [
            "University KPIs", "University KPIs", "University KPIs",
            "Operational KPIs", "Operational KPIs", "Operational KPIs", "Operational KPIs",
            "Business KPIs", "Business KPIs", "Business KPIs", "Business KPIs", "Business KPIs",
            "Engagement KPIs", "Engagement KPIs", "Engagement KPIs", "Engagement KPIs"
        ],
        "Metric Name": [
            "Total Orders", "Food Orders", "Stationery Orders",
            "Avg Waiting Time", "Queue Reduction Rate", "Avg Pickup Time", "Slot Utilization",
            "Revenue", "Refunds", "Cancellation Rate", "User Growth", "Vendor Growth",
            "Active Users", "Returning Users", "Vouchers Redeemed", "Points Redeemed"
        ],
        "Value": [
            kpis["university_kpis"]["total_orders"],
            kpis["university_kpis"]["food_orders"],
            kpis["university_kpis"]["stationery_orders"],
            f"{kpis['operational_kpis']['avg_waiting_time_minutes']} mins",
            f"{kpis['operational_kpis']['queue_reduction_pct']}%",
            f"{kpis['operational_kpis']['avg_pickup_time_minutes']} mins",
            f"{kpis['operational_kpis']['slot_utilization_pct']}%",
            f"INR {kpis['business_kpis']['revenue_inr']:.2f}",
            f"INR {kpis['business_kpis']['refunds_inr']:.2f}",
            f"{kpis['business_kpis']['cancellation_rate_pct']}%",
            kpis["business_kpis"]["user_growth_count"],
            kpis["business_kpis"]["vendor_growth_count"],
            kpis["engagement_kpis"]["active_users"],
            kpis["engagement_kpis"]["returning_users"],
            kpis["engagement_kpis"]["vouchers_redeemed_count"],
            f"{kpis['engagement_kpis']['points_redeemed']:.1f} pts"
        ]
    }
    df_overview = pd.DataFrame(overview_data)

    # Sheet 2: Daily Trends
    trends = kpis["university_kpis"]["daily_trend"]
    df_trends = pd.DataFrame(trends) if trends else pd.DataFrame(columns=["date", "count"])
    df_trends.columns = ["Date", "Orders Count"]

    # Sheet 3: Vendor Performance
    vendors = kpis["operational_kpis"]["vendor_performance"]
    df_vendors = pd.DataFrame(vendors) if vendors else pd.DataFrame(columns=[
        "vendor_id", "vendor_name", "orders_count", "completion_rate", "avg_wait_minutes", "rating", "score"
    ])
    if not df_vendors.empty:
        df_vendors.columns = ["Vendor ID", "Vendor Name", "Orders Processed", "Completion Rate (%)", "Avg Prep Time (mins)", "Avg Rating", "Score"]

    # Write sheets to BytesIO Excel workbook
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_overview.to_excel(writer, sheet_name="KPI Overview", index=False)
        df_trends.to_excel(writer, sheet_name="Daily Trends", index=False)
        df_vendors.to_excel(writer, sheet_name="Vendor Performance", index=False)

    output.seek(0)
    return output


def generate_kpi_pdf(kpis: Dict[str, Any]) -> io.BytesIO:
    """Generate structured executive PDF report of KPIs using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#6B7280'),
        spaceAfter=20
    )

    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#111827'),
        spaceBefore=15,
        spaceAfter=10
    )

    body_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#374151')
    )

    header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.white
    )

    # Document Header
    story.append(Paragraph("Institutional KPI Executive Summary", title_style))
    
    filters = kpis["filters"]
    date_range = f"Date Range: {filters['date_from']} to {filters['date_to']}"
    dept_val = filters.get("department")
    dept_str = f"Department: {dept_val}" if dept_val else "Department: All Departments"
    vendor_val = filters.get("vendor_id")
    vendor_str = f"Vendor: Vendor ID {vendor_val}" if vendor_val else "Vendor: All Vendors"
    
    meta_para = f"{date_range}   |   {dept_str}   |   {vendor_str}   |   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    story.append(Paragraph(meta_para, subtitle_style))
    story.append(Spacer(1, 10))

    # --- Section: KPI Metrics Summary Table ---
    story.append(Paragraph("Core Metric Performance Overview", section_style))

    summary_headers = [
        Paragraph("University KPIs", header_style),
        Paragraph("Value", header_style),
        Paragraph("Operational KPIs", header_style),
        Paragraph("Value", header_style)
    ]

    u_kpis = kpis["university_kpis"]
    op_kpis = kpis["operational_kpis"]
    b_kpis = kpis["business_kpis"]
    en_kpis = kpis["engagement_kpis"]

    summary_rows = [
        [
            Paragraph("Total Orders", body_style), Paragraph(str(u_kpis["total_orders"]), body_style),
            Paragraph("Avg Waiting Time", body_style), Paragraph(f"{op_kpis['avg_waiting_time_minutes']} mins", body_style)
        ],
        [
            Paragraph("Food Orders", body_style), Paragraph(str(u_kpis["food_orders"]), body_style),
            Paragraph("Queue Reduction Rate", body_style), Paragraph(f"{op_kpis['queue_reduction_pct']}%", body_style)
        ],
        [
            Paragraph("Stationery Orders", body_style), Paragraph(str(u_kpis["stationery_orders"]), body_style),
            Paragraph("Avg Pickup Time", body_style), Paragraph(f"{op_kpis['avg_pickup_time_minutes']} mins", body_style)
        ],
        [
            Paragraph("Revenue (INR)", body_style), Paragraph(f"INR {b_kpis['revenue_inr']:.2f}", body_style),
            Paragraph("Slot Utilization", body_style), Paragraph(f"{op_kpis['slot_utilization_pct']}%", body_style)
        ],
        [
            Paragraph("Refunds (INR)", body_style), Paragraph(f"INR {b_kpis['refunds_inr']:.2f}", body_style),
            Paragraph("Active Users", body_style), Paragraph(str(en_kpis["active_users"]), body_style)
        ],
        [
            Paragraph("Cancellation Rate", body_style), Paragraph(f"{b_kpis['cancellation_rate_pct']}%", body_style),
            Paragraph("Returning Users", body_style), Paragraph(str(en_kpis["returning_users"]), body_style)
        ],
        [
            Paragraph("User Growth (Signups)", body_style), Paragraph(str(b_kpis["user_growth_count"]), body_style),
            Paragraph("Vouchers Redeemed", body_style), Paragraph(str(en_kpis["vouchers_redeemed_count"]), body_style)
        ],
        [
            Paragraph("Vendor Growth (New)", body_style), Paragraph(str(b_kpis["vendor_growth_count"]), body_style),
            Paragraph("Points Redeemed", body_style), Paragraph(f"{en_kpis['points_redeemed']:.1f} pts", body_style)
        ]
    ]

    t_data = [summary_headers] + summary_rows
    summary_table = Table(t_data, colWidths=[150, 110, 150, 110])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # --- Section: Vendor Performance Table ---
    story.append(Paragraph("Vendor Performance Rankings", section_style))

    vendor_headers = [
        Paragraph("Vendor Name", header_style),
        Paragraph("Orders Processed", header_style),
        Paragraph("Completion Rate (%)", header_style),
        Paragraph("Avg Prep Time (mins)", header_style),
        Paragraph("Avg Rating", header_style)
    ]

    vendor_rows = []
    for vp in op_kpis["vendor_performance"]:
        vendor_rows.append([
            Paragraph(vp["vendor_name"], body_style),
            Paragraph(str(vp["orders_count"]), body_style),
            Paragraph(f"{vp['completion_rate']}%", body_style),
            Paragraph(f"{vp['avg_wait_minutes']}m", body_style),
            Paragraph(f"{vp['rating']} / 5.0", body_style),
        ])

    if not vendor_rows:
        vendor_rows.append([Paragraph("No vendor activity reported.", body_style), "", "", "", ""])

    v_data = [vendor_headers] + vendor_rows
    vendor_table = Table(v_data, colWidths=[180, 100, 100, 100, 40])
    vendor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#312E81')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(vendor_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

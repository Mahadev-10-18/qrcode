import qrcode
import base64
from io import BytesIO


def tag_to_html(tag) -> str:
    """Return HTML snippet for a single tag with QR image and label."""
    # Build URL for QR code
    from ..config import settings
    domain = settings.domain

    qr_url = f"https://{domain}/t/{tag.id}"
    # Generate QR PNG in memory
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    # Simple HTML block
    return f"""
    <div class='tag-cell'>
        <img src='data:image/png;base64,{b64}' alt='QR' class='qr-img'/>
        <div class='label'>{tag.label}</div>
    </div>
    """


def render_grid_html(tags, per_page: int = 6) -> str:
    """Render a full HTML document containing a grid of tags.
    `per_page` can be 6 (2x3) or 12 (3x4)."""
    cols = 3 if per_page == 6 else 4
    rows = per_page // cols
    cells_html = "\n".join(tag_to_html(tag) for tag in tags)
    # Pad empty cells if needed
    total_cells = rows * cols
    empty_cells = total_cells - len(tags)
    cells_html += "\n" + "\n".join("<div class='tag-cell'></div>" for _ in range(empty_cells))
    html = f"""
    <html><head>
    <style>
        body {{ margin:0; padding:0; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat({cols}, 1fr);
            grid-template-rows: repeat({rows}, 1fr);
            gap: 5mm;
            page-break-after: always;
        }}
        .tag-cell {{
            border: 1px dashed #888;
            text-align: center;
            padding: 2mm;
        }}
        .qr-img {{ width: 40mm; height: 40mm; }}
        .label {{ margin-top: 2mm; font-size: 10pt; }}
    </style>
    </head><body>
    <div class='grid'>
    {cells_html}
    </div>
    </body></html>
    """
    return html


def html_to_pdf(html: str) -> bytes:
    from xhtml2pdf import pisa
    from io import BytesIO
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if pdf.err:
        raise RuntimeError("PDF generation failed")
    return result.getvalue()

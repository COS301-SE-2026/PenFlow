from pathlib import Path

from weasyprint import CSS, HTML


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"
REPORT_STYLESHEET_NAME = "report_styles.css"


def generate_pdf_from_html(html_content: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stylesheet_path = TEMPLATE_DIR / REPORT_STYLESHEET_NAME

    HTML(
        string=html_content,
        base_url=str(TEMPLATE_DIR),
    ).write_pdf(
        str(output_path),
        stylesheets=[CSS(filename=str(stylesheet_path))],
    )

    return output_path
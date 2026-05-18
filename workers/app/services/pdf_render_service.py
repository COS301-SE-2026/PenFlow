from pathlib import Path
from weasyprint import HTML

def generate_pdf_from_html(html_content: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    HTML(
        string=html_content,
        base_url=str(output_path.parent),
    ).write_pdf(str(output_path))

    return output_path
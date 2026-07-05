from unittest.mock import MagicMock, patch

from app.services import pdf_render_service
from app.services.pdf_render_service import generate_pdf_from_html

@patch("app.services.pdf_render_service.CSS")
@patch("app.services.pdf_render_service.HTML")
def test_generate_pdf_from_html(mock_html, mock_css, tmp_path):
    html_body = "<h1>Testing Report<h1>"
    output_path = tmp_path / "reports" / "scan-1234" / "report.pdf"

    mock_html_inst = MagicMock()
    mock_html.return_value = mock_html_inst

    result = generate_pdf_from_html(html_body, output_path)
    
    assert result == output_path
    assert output_path.parent.exists()

    mock_html.assert_called_once_with(
        string=html_body,
        base_url=str(pdf_render_service.TEMPLATE_DIR),
    )

    mock_css.assert_called_once_with(
        filename=str(pdf_render_service.TEMPLATE_DIR / pdf_render_service.REPORT_STYLESHEET_NAME)
    )

    mock_html_inst.write_pdf.assert_called_once_with(
        str(output_path),
        stylesheets=[mock_css.return_value],
    )
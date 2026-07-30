from unittest.mock import MagicMock, patch

from app.services.pdf_renderer import generate_pdf_from_html


#phase2  download pdf test
@patch("app.services.pdf_renderer.CSS")
@patch("app.services.pdf_renderer.HTML")
def test_generate_pdf_from_html(mock_html, mock_css, tmp_path):
    out_path = tmp_path / "reports" / "report.pdf"
    html_inst = MagicMock()
    mock_html.return_value = html_inst

    result = generate_pdf_from_html("<h1>Test</h1>", out_path)
    
    assert result == out_path
    assert out_path.parent.exists()

    mock_html.assert_called_once_with(
        string= "<h1>Test</h1>", 
        base_url="/app",
    )

    mock_css.assert_called_once()
    html_inst.write_pdf.assert_called_once()
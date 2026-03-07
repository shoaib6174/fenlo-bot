"""Tests for file upload security validator."""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.services.file_validator import (
    MAX_FILE_SIZE_BYTES,
    FileValidationError,
    FileValidator,
    get_file_validator,
)


@pytest.fixture
def file_validator():
    """Create FileValidator instance with mocked magic."""
    with patch("app.services.file_validator.magic.Magic"):
        validator = FileValidator()
        validator.magic = MagicMock()
        return validator


class TestFileValidator:
    """Test FileValidator class."""

    async def test_validate_pdf_success(self, file_validator):
        """Test validating a legitimate PDF file."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n%%EOF"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        # Should not raise
        await file_validator.validate(pdf_content, "test.pdf")

    async def test_validate_docx_success(self, file_validator):
        """Test validating a legitimate DOCX file."""
        docx_content = b"PK\x03\x04"  # ZIP magic bytes (DOCX is a zip)
        file_validator.magic.from_buffer.return_value = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        await file_validator.validate(docx_content, "test.docx")

    async def test_validate_text_file_success(self, file_validator):
        """Test validating text files."""
        text_content = b"Plain text content"
        file_validator.magic.from_buffer.return_value = "text/plain"

        await file_validator.validate(text_content, "test.txt")

    async def test_validate_csv_success(self, file_validator):
        """Test validating CSV files."""
        csv_content = b"col1,col2\nval1,val2"
        file_validator.magic.from_buffer.return_value = "text/csv"

        await file_validator.validate(csv_content, "test.csv")

    async def test_validate_markdown_success(self, file_validator):
        """Test validating Markdown files."""
        md_content = b"# Heading\n\nParagraph"
        file_validator.magic.from_buffer.return_value = "text/markdown"

        await file_validator.validate(md_content, "test.md")

    async def test_validate_rejects_empty_file(self, file_validator):
        """Test that empty files are rejected."""
        with pytest.raises(FileValidationError, match="Empty file not allowed"):
            await file_validator.validate(b"", "empty.pdf")

    async def test_validate_rejects_disallowed_mime_type(self, file_validator):
        """Test that disallowed MIME types are rejected."""
        exe_content = b"MZ\x90\x00"  # PE executable magic bytes
        file_validator.magic.from_buffer.return_value = "application/x-executable"

        with pytest.raises(FileValidationError, match="File type not allowed"):
            await file_validator.validate(exe_content, "malware.pdf")

    async def test_validate_rejects_html_file(self, file_validator):
        """Test that HTML files are rejected (XSS risk)."""
        html_content = b"<html><script>alert('xss')</script></html>"
        file_validator.magic.from_buffer.return_value = "text/html"

        with pytest.raises(FileValidationError, match="File type not allowed"):
            await file_validator.validate(html_content, "page.html")

    async def test_validate_rejects_zip_file(self, file_validator):
        """Test that generic ZIP files are rejected (zip bomb risk)."""
        zip_content = b"PK\x03\x04"
        file_validator.magic.from_buffer.return_value = "application/zip"

        with pytest.raises(FileValidationError, match="File type not allowed"):
            await file_validator.validate(zip_content, "archive.zip")

    async def test_validate_rejects_oversized_file(self, file_validator):
        """Test that files exceeding size limit are rejected."""
        large_content = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        file_validator.magic.from_buffer.return_value = "application/pdf"

        with pytest.raises(FileValidationError, match="File too large"):
            await file_validator.validate(large_content, "huge.pdf")

    async def test_validate_accepts_max_size_file(self, file_validator):
        """Test that files at exactly max size are accepted."""
        max_content = b"x" * MAX_FILE_SIZE_BYTES
        file_validator.magic.from_buffer.return_value = "application/pdf"

        # Should not raise
        await file_validator.validate(max_content, "maxsize.pdf")

    async def test_validate_warns_on_embedded_javascript(self, file_validator):
        """Test that PDFs with embedded JavaScript trigger warnings."""
        pdf_with_js = b"%PDF-1.4\n/JavaScript (app.alert('test'))\n%%EOF"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        with patch("app.services.file_validator.logger") as mock_logger:
            await file_validator.validate(pdf_with_js, "script.pdf")

            # Verify warning was logged
            assert any(
                call[0][0] == "file_validator.embedded_script_detected"
                for call in mock_logger.warning.call_args_list
            )

    async def test_validate_detects_js_tag_case_insensitive(self, file_validator):
        """Test that JavaScript detection is case-insensitive."""
        pdf_with_js_upper = b"%PDF-1.4\n/JAVASCRIPT\n%%EOF"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        with patch("app.services.file_validator.logger") as mock_logger:
            await file_validator.validate(pdf_with_js_upper, "script.pdf")

            # Should still detect uppercase JavaScript tag
            assert any(
                call[0][0] == "file_validator.embedded_script_detected"
                for call in mock_logger.warning.call_args_list
            )

    async def test_validate_detects_js_short_tag(self, file_validator):
        """Test that /JS tag (short form) is also detected."""
        pdf_with_js = b"%PDF-1.4\n/JS (code)\n%%EOF"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        with patch("app.services.file_validator.logger") as mock_logger:
            await file_validator.validate(pdf_with_js, "script.pdf")

            assert any(
                call[0][0] == "file_validator.embedded_script_detected"
                for call in mock_logger.warning.call_args_list
            )

    async def test_validate_handles_file_like_object(self, file_validator):
        """Test that file-like objects are handled correctly."""
        content = b"Plain text content"
        file_like = io.BytesIO(content)
        file_validator.magic.from_buffer.return_value = "text/plain"

        await file_validator.validate(file_like, "test.txt")

        # Verify file position was reset
        assert file_like.tell() == 0

    async def test_validate_logs_start_and_success(self, file_validator):
        """Test that validation logs start and success events."""
        pdf_content = b"%PDF-1.4\n%%EOF"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        with patch("app.services.file_validator.logger") as mock_logger:
            await file_validator.validate(pdf_content, "test.pdf")

            # Verify logging calls
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert "file_validator.validate_start" in log_calls
            assert "file_validator.validate_success" in log_calls

    def test_is_pdf_detects_pdf(self, file_validator):
        """Test _is_pdf correctly identifies PDF files."""
        pdf_content = b"%PDF-1.4"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        assert file_validator._is_pdf(pdf_content) is True

    def test_is_pdf_rejects_non_pdf(self, file_validator):
        """Test _is_pdf correctly rejects non-PDF files."""
        text_content = b"Plain text"
        file_validator.magic.from_buffer.return_value = "text/plain"

        assert file_validator._is_pdf(text_content) is False


class TestFileValidatorSingleton:
    """Test get_file_validator singleton pattern."""

    def test_get_file_validator_returns_singleton(self):
        """Test that get_file_validator returns the same instance."""
        with patch("app.services.file_validator.magic.Magic"):
            validator1 = get_file_validator()
            validator2 = get_file_validator()

            assert validator1 is validator2


class TestParseSubprocessSafety:
    """Test parse safety validation (Layer 3)."""

    async def test_validate_parse_safety_placeholder(self, file_validator):
        """Test that parse safety validation exists (placeholder for now)."""
        # This is a placeholder test for Layer 3
        # Real implementation will parse in subprocess with timeout

        content = b"test content"
        # Should not raise (placeholder implementation is a pass)
        await file_validator._validate_parse_safety(content, "test.txt")


class TestScriptStripping:
    """Test embedded script detection and stripping (Layer 4)."""

    async def test_clean_pdf_passes(self, file_validator):
        """Test that clean PDFs pass script validation."""
        clean_pdf = b"%PDF-1.4\n/Type /Catalog\n%%EOF"
        file_validator.magic.from_buffer.return_value = "application/pdf"

        # Should not raise or warn about scripts
        with patch("app.services.file_validator.logger") as mock_logger:
            await file_validator._validate_no_embedded_scripts(clean_pdf, "clean.pdf")

            # Should not have logged embedded script warning
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert "file_validator.embedded_script_detected" not in warning_calls

    async def test_script_stripping_non_pdf_skipped(self, file_validator):
        """Test that script validation is only applied to PDFs."""
        # For non-PDF files, _validate_no_embedded_scripts should not be called
        text_content = b"Plain text with /JavaScript tag"
        file_validator.magic.from_buffer.return_value = "text/plain"

        await file_validator.validate(text_content, "test.txt")

        # Should pass (script check only for PDFs)

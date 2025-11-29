"""
Document Parser Agent

Extracts text from PDF documents using multiple methods.
This is a deterministic agent (no LLM required).
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import PyPDF2
import pdfplumber

from src.utils.logging import setup_logger
from src.schemas.report import DownloadedReport, ParsedReportContent


class DocumentParserAgent:
    """
    Agent for extracting text from PDF documents.

    Uses a multi-method approach:
    1. PyPDF2 (fast, good for standard PDFs)
    2. pdfplumber (slower but handles complex layouts better)

    This agent is deterministic and doesn't require LLM capabilities.
    """

    def __init__(self):
        """Initialize the document parser agent."""
        self.name = "DocumentParser"
        self.logger = setup_logger(self.name)
        self.logger.info("Document Parser Agent initialized")

    def execute(
        self,
        report: DownloadedReport,
        cache_dir: Optional[str] = None
    ) -> ParsedReportContent:
        """
        Extract text from a PDF report.

        Args:
            report: DownloadedReport with file metadata
            cache_dir: Directory containing the PDF file

        Returns:
            ParsedReportContent with extracted text

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If extraction fails with all methods
        """
        self.logger.info(f"Parsing document: {report.filename}")

        # Determine file path
        if cache_dir:
            file_path = Path(cache_dir) / report.filename
        else:
            # Try to extract from URL if it's a file:// URL
            if report.url.startswith("file://"):
                file_path = Path(report.url.replace("file://", ""))
            else:
                raise ValueError(
                    "cache_dir must be provided or report.url must be a file:// URL"
                )

        # Validate file exists
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        self.logger.info(f"Reading PDF from: {file_path}")

        # Try extraction with PyPDF2 first
        try:
            self.logger.info("Attempting extraction with PyPDF2...")
            result = self._extract_with_pypdf2(file_path, report.filename)

            # Check if extraction was meaningful
            if result.char_count > 100:  # At least 100 characters
                self.logger.info(f"✓ PyPDF2 extraction successful ({result.char_count:,} chars)")
                return result
            else:
                self.logger.warning("PyPDF2 extraction produced minimal text, trying pdfplumber...")
        except Exception as e:
            self.logger.warning(f"PyPDF2 extraction failed: {e}, trying pdfplumber...")

        # Fallback to pdfplumber
        try:
            self.logger.info("Attempting extraction with pdfplumber...")
            result = self._extract_with_pdfplumber(file_path, report.filename)

            if result.char_count > 100:
                self.logger.info(f"✓ pdfplumber extraction successful ({result.char_count:,} chars)")
                return result
            else:
                self.logger.error("All extraction methods failed to produce meaningful text")
                # Return minimal result
                return ParsedReportContent(
                    filename=report.filename,
                    full_text="",
                    summary_section=None,
                    page_count=0,
                    extraction_method="failed",
                    char_count=0,
                    extraction_date=datetime.now(),
                    extraction_successful=False
                )
        except Exception as e:
            self.logger.error(f"pdfplumber extraction failed: {e}")
            return ParsedReportContent(
                filename=report.filename,
                full_text="",
                summary_section=None,
                page_count=0,
                extraction_method="failed",
                char_count=0,
                extraction_date=datetime.now(),
                extraction_successful=False
            )

    def _extract_with_pypdf2(
        self,
        file_path: Path,
        filename: str
    ) -> ParsedReportContent:
        """
        Extract text using PyPDF2.

        Args:
            file_path: Path to PDF file
            filename: Original filename

        Returns:
            ParsedReportContent with extracted text
        """
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            # Extract text from all pages
            full_text = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                except Exception as e:
                    self.logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

            full_text_str = "\n\n".join(full_text)

            # Extract summary from first page (first 1500 chars)
            summary_section = None
            if full_text:
                first_page = full_text[0]
                summary_section = first_page[:1500] if len(first_page) > 1500 else first_page

            return ParsedReportContent(
                filename=filename,
                full_text=full_text_str,
                summary_section=summary_section,
                page_count=page_count,
                extraction_method="PyPDF2",
                char_count=len(full_text_str),
                extraction_date=datetime.now(),
                extraction_successful=True
            )

    def _extract_with_pdfplumber(
        self,
        file_path: Path,
        filename: str
    ) -> ParsedReportContent:
        """
        Extract text using pdfplumber.

        This method is more robust for complex layouts but slower.

        Args:
            file_path: Path to PDF file
            filename: Original filename

        Returns:
            ParsedReportContent with extracted text
        """
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)

            # Extract text from all pages
            full_text = []
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                except Exception as e:
                    self.logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

            full_text_str = "\n\n".join(full_text)

            # Extract summary from first page (first 1500 chars)
            summary_section = None
            if full_text:
                first_page = full_text[0]
                summary_section = first_page[:1500] if len(first_page) > 1500 else first_page

            return ParsedReportContent(
                filename=filename,
                full_text=full_text_str,
                summary_section=summary_section,
                page_count=page_count,
                extraction_method="pdfplumber",
                char_count=len(full_text_str),
                extraction_date=datetime.now(),
                extraction_successful=True
            )

    def extract_from_file(self, file_path: str) -> ParsedReportContent:
        """
        Convenience method to extract text from a file path directly.

        Args:
            file_path: Path to PDF file

        Returns:
            ParsedReportContent with extracted text
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Create a minimal DownloadedReport
        from src.schemas.report import DownloadedReport, ReportStatus

        report = DownloadedReport(
            url=f"file://{file_path}",
            filename=file_path.name,
            download_date=datetime.fromtimestamp(file_path.stat().st_mtime),
            file_size_bytes=file_path.stat().st_size,
            status=ReportStatus.DOWNLOADED
        )

        return self.execute(report, cache_dir=str(file_path.parent))

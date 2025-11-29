"""
Report Data Schemas

Defines data structures for downloaded reports and extracted data.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class ReportStatus(str, Enum):
    """Status of a report."""
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    PARSED = "parsed"
    ANALYZED = "analyzed"
    FAILED = "failed"


class DownloadedReport(BaseModel):
    """Metadata for a downloaded report."""
    
    url: str = Field(..., description="URL where report was downloaded from")
    filename: str = Field(..., description="Local filename of downloaded PDF")
    download_date: datetime = Field(..., description="When the report was downloaded")
    file_size_bytes: int = Field(..., description="Size of downloaded file")
    report_date: Optional[date] = Field(None, description="Date the report covers")
    status: ReportStatus = Field(ReportStatus.DOWNLOADED, description="Processing status")


class ParsedReportContent(BaseModel):
    """Extracted text content from a report."""
    
    filename: str = Field(..., description="Source filename")
    full_text: str = Field(..., description="Complete extracted text")
    summary_section: Optional[str] = Field(None, description="First page summary")
    page_count: int = Field(..., description="Number of pages in PDF")
    extraction_method: str = Field(..., description="Method used (PyPDF2, pdfplumber)")
    char_count: int = Field(..., description="Total characters extracted")
    extraction_date: datetime = Field(..., description="When text was extracted")
    extraction_successful: bool = Field(..., description="Whether extraction succeeded")


class FluDataExtraction(BaseModel):
    """
    Structured flu data extracted by Gemini from report text.
    
    This is what the Report Analyst Agent produces.
    """
    
    flu_level: int = Field(
        ..., 
        ge=1, 
        le=10, 
        description="Estimated flu activity level (1=minimal, 10=very high)"
    )
    trend: str = Field(
        ..., 
        description="Trend: increasing, stable, decreasing, rapid_increase, rapid_decrease"
    )
    ili_rate_per_100k: Optional[float] = Field(
        None, 
        description="ILI consultation rate per 100,000 population"
    )
    confirmed_cases: Optional[int] = Field(
        None, 
        description="Number of laboratory-confirmed influenza cases"
    )
    dominant_strain: Optional[str] = Field(
        None, 
        description="Dominant influenza strain (e.g., A(H3N2), B/Victoria)"
    )
    positivity_rate: Optional[float] = Field(
        None, 
        ge=0, 
        le=100, 
        description="Percentage of samples testing positive for influenza"
    )
    alerts: List[str] = Field(
        default_factory=list, 
        description="Any warnings or alerts mentioned"
    )
    regional_data: Optional[dict] = Field(
        None, 
        description="Regional breakdown if available"
    )
    confidence: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Confidence in extraction accuracy (0-1)"
    )
    summary: str = Field(
        ..., 
        description="Brief English summary of the report"
    )
    week_number: Optional[int] = Field(
        None, 
        description="Epidemiological week number"
    )
    report_period: Optional[str] = Field(
        None, 
        description="Time period covered by report"
    )


class ReportAnalysisResult(BaseModel):
    """
    Complete result from Report Ingestion system.
    
    Combines all stages: download, parse, analysis.
    """
    
    downloaded_report: DownloadedReport = Field(..., description="Download metadata")
    parsed_content: ParsedReportContent = Field(..., description="Extracted text")
    flu_data: FluDataExtraction = Field(..., description="Analyzed flu data")
    processing_time_seconds: float = Field(..., description="Total processing time")
    success: bool = Field(..., description="Overall success status")
    error_message: Optional[str] = Field(None, description="Error if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "downloaded_report": {
                    "url": "https://eody.gov.gr/report.pdf",
                    "filename": "eody_2024_w47.pdf",
                    "download_date": "2024-11-20T10:00:00",
                    "file_size_bytes": 524288,
                    "status": "analyzed"
                },
                "flu_data": {
                    "flu_level": 5,
                    "trend": "increasing",
                    "ili_rate_per_100k": 58.3,
                    "confidence": 0.85,
                    "summary": "Moderate flu activity with increasing trend"
                },
                "success": True
            }
        }
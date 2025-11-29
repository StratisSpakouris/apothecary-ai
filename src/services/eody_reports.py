"""
EODY Reports Service

Loads processed EODY report data (manually uploaded and analyzed).
"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class EODYReportsService:
    """
    Service for loading processed EODY flu surveillance reports.
    
    Reports are:
    1. Manually downloaded from EODY website
    2. Uploaded to data/eody_reports/uploads/
    3. Processed by process_eody_reports.py script
    4. Results stored in data/eody_reports/processed/
    """
    
    def __init__(self, processed_dir: str = "data/eody_reports/processed"):
        """
        Initialize EODY Reports Service.
        
        Args:
            processed_dir: Directory containing processed report JSON files
        """
        self.processed_dir = Path(processed_dir)
        self._cached_reports: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def get_latest_report(self) -> Optional[Dict]:
        """
        Get the most recently processed report.
        
        Returns:
            Dict with flu data from latest report, or None if no reports
        """
        reports = self._load_reports()
        
        if not reports:
            logger.warning("No processed EODY reports found")
            return None
        
        # Sort by processed date, most recent first
        sorted_reports = sorted(
            reports,
            key=lambda r: r.get('processed_date', ''),
            reverse=True
        )
        
        latest = sorted_reports[0]
        logger.info(f"Using latest report: {latest['filename']}")
        
        return latest['flu_data']
    
    def get_all_reports(self) -> List[Dict]:
        """
        Get all processed reports.
        
        Returns:
            List of report data dictionaries
        """
        return self._load_reports()
    
    def _load_reports(self) -> List[Dict]:
        """
        Load processed reports from JSON files.
        
        Returns:
            List of report dictionaries
        """
        # Check cache (valid for 1 hour)
        if self._cached_reports and self._cache_timestamp:
            age = datetime.now() - self._cache_timestamp
            if age.total_seconds() < 3600:
                return self._cached_reports
        
        reports = []
        
        # Check for combined summary file first
        summary_file = self.processed_dir / "all_reports_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    reports = data.get('reports', [])
                    logger.info(f"Loaded {len(reports)} reports from summary file")
            except Exception as e:
                logger.error(f"Failed to load summary file: {e}")
        
        # If no summary, load individual files
        if not reports and self.processed_dir.exists():
            for json_file in self.processed_dir.glob("*_analysis.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        reports.append(report)
                except Exception as e:
                    logger.error(f"Failed to load {json_file}: {e}")
            
            logger.info(f"Loaded {len(reports)} individual report files")
        
        # Update cache
        self._cached_reports = reports
        self._cache_timestamp = datetime.now()
        
        return reports
    
    def has_reports(self) -> bool:
        """
        Check if any processed reports are available.
        
        Returns:
            True if reports exist
        """
        return len(self._load_reports()) > 0
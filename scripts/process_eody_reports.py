"""
Process Manually Uploaded EODY Reports

Scans the uploads directory for PDFs, extracts text,
and analyzes them with Gemini to produce flu data.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.document_parser import DocumentParserAgent
from src.agents.report_analyst import ReportAnalystAgent
from src.schemas.report import DownloadedReport, ReportStatus
from datetime import datetime
import json


def main():
    print("=" * 70)
    print("EODY REPORT PROCESSOR")
    print("=" * 70)
    
    # Configuration
    uploads_dir = Path("data/eody_reports/uploads")
    output_dir = Path("data/eody_reports/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDFs in uploads directory
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("\n⚠ No PDF files found in uploads directory!")
        print(f"   Directory: {uploads_dir}")
        print("\n   Please:")
        print("   1. Download EODY reports from: https://eody.gov.gr/el/anakoinoseis.html")
        print(f"   2. Place PDFs in: {uploads_dir}/")
        print("   3. Run this script again")
        return
    
    print(f"\n✓ Found {len(pdf_files)} PDF(s) in uploads directory")
    print("-" * 70)
    
    # Initialize agents
    parser = DocumentParserAgent()
    analyst = ReportAnalystAgent()
    
    results = []
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        print("-" * 70)
        
        try:
            # Create DownloadedReport metadata
            report = DownloadedReport(
                url=f"file://{pdf_path}",
                filename=pdf_path.name,
                download_date=datetime.fromtimestamp(pdf_path.stat().st_mtime),
                file_size_bytes=pdf_path.stat().st_size,
                report_date=None,
                status=ReportStatus.DOWNLOADED
            )
            
            # Step 1: Parse PDF
            print("   [1/2] Extracting text from PDF...")
            parsed = parser.execute(
                report=report,
                cache_dir=str(uploads_dir)
            )
            
            if not parsed.extraction_successful:
                print("   ❌ Failed to extract text")
                continue
            
            print(f"   ✓ Extracted {parsed.char_count:,} characters")
            print(f"   ✓ Method: {parsed.extraction_method}")
            print(f"   ✓ Pages: {parsed.page_count}")
            
            # Show preview of extracted text
            if parsed.summary_section:
                preview = parsed.summary_section[:300]
                print(f"\n   Preview (first 300 chars):")
                print(f"   {preview}...")
            
            # Step 2: Analyze with Gemini
            print("\n   [2/2] Analyzing with Gemini...")
            flu_data = analyst.execute(parsed)
            
            print(f"   ✓ Analysis complete")
            print(f"   ✓ Flu level: {flu_data.flu_level}/10 ({flu_data.trend})")
            print(f"   ✓ Confidence: {flu_data.confidence:.0%}")
            
            # Store result
            result = {
                "filename": pdf_path.name,
                "processed_date": datetime.now().isoformat(),
                "extraction": {
                    "success": parsed.extraction_successful,
                    "method": parsed.extraction_method,
                    "char_count": parsed.char_count,
                    "page_count": parsed.page_count
                },
                "flu_data": {
                    "flu_level": flu_data.flu_level,
                    "trend": flu_data.trend,
                    "ili_rate_per_100k": flu_data.ili_rate_per_100k,
                    "confirmed_cases": flu_data.confirmed_cases,
                    "dominant_strain": flu_data.dominant_strain,
                    "positivity_rate": flu_data.positivity_rate,
                    "alerts": flu_data.alerts,
                    "confidence": flu_data.confidence,
                    "summary": flu_data.summary,
                    "week_number": flu_data.week_number,
                    "report_period": flu_data.report_period
                }
            }
            
            results.append(result)
            
            # Save individual result
            result_file = output_dir / f"{pdf_path.stem}_analysis.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"   ✓ Saved: {result_file.name}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    
    if results:
        print(f"\n✓ Successfully processed {len(results)}/{len(pdf_files)} reports")
        
        # Save combined results
        combined_file = output_dir / "all_reports_summary.json"
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump({
                "processed_date": datetime.now().isoformat(),
                "total_reports": len(results),
                "reports": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Combined results saved to: {combined_file}")
        
        # Show flu levels
        print("\n📊 Flu Activity Levels:")
        for result in results:
            print(f"   • {result['filename']}: Level {result['flu_data']['flu_level']}/10 ({result['flu_data']['trend']})")
        
        # Show average
        avg_level = sum(r['flu_data']['flu_level'] for r in results) / len(results)
        print(f"\n   Average level: {avg_level:.1f}/10")
        
    else:
        print("\n⚠ No reports were successfully processed")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
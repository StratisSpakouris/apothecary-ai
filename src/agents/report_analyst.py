"""
Report Analyst Agent

Uses Google ADK and Gemini to analyze flu surveillance reports.
Extracts structured data from Greek EODY reports.
"""

import json
import re
import asyncio
from typing import Optional
from datetime import datetime

from google.adk.runners import InMemoryRunner
from src.agents.adk_base_agent import ADKAgent
from src.schemas.report import ParsedReportContent, FluDataExtraction


class ReportAnalystAgent(ADKAgent):
    """
    Agent that analyzes flu surveillance reports using Gemini via Google ADK.

    This agent:
    - Takes extracted text from EODY reports (in Greek)
    - Uses Gemini to understand the content
    - Extracts structured flu data in English
    - Returns FluDataExtraction with confidence scores

    Built on Google ADK for robust LLM orchestration.
    """

    ANALYSIS_INSTRUCTION = """You are an expert epidemiologist analyzing Greek flu surveillance reports from EODY (National Public Health Organization).

Your task is to extract structured data from Greek flu/influenza surveillance reports and provide it in Greek.

Key information to extract:
1. **Flu Activity Level** (1-10 scale):
   - 1-2: Minimal activity
   - 3-4: Low activity
   - 5-6: Moderate activity
   - 7-8: High activity
   - 9-10: Very high activity
   Look for: "επίπεδο δραστηριότητας", "έντασης", ILI rates, case numbers

2. **Trend** (must be one of):
   - "increasing": Activity is rising
   - "stable": Activity is steady
   - "decreasing": Activity is declining
   - "rapid_increase": Sharp rise in activity
   - "rapid_decrease": Sharp decline in activity
   Look for: week-over-week changes, phrases like "αύξηση", "μείωση", "σταθερή"

3. **ILI Rate per 100k**: Look for "ποσοστό συμβουλών ILI ανά 100.000"

4. **Confirmed Cases**: Number of laboratory-confirmed influenza cases

5. **Dominant Strain**: e.g., A(H3N2), A(H1N1), B/Victoria, B/Yamagata
   Look for: "κυρίαρχο στέλεχος", virus type mentions

6. **Positivity Rate**: Percentage of samples testing positive for influenza
   Look for: "θετικότητα", "ποσοστό θετικών"

7. **Alerts**: Any warnings, alerts, or special mentions

8. **Week Number**: Epidemiological week number

9. **Confidence** (0-1): Your confidence in the extraction accuracy based on:
   - Text clarity: 0.9-1.0 for clear, well-structured reports
   - Partial data: 0.6-0.8 for incomplete but usable data
   - Poor quality: 0.3-0.5 for unclear or minimal data

10. **Summary**: Brief 2-3 sentence English summary of the report

IMPORTANT:
- All output must be in English, even though input is in Greek
- If a field is not found, use null (not 0 or empty string)
- Be conservative with confidence scores
- Flu level should reflect overall activity, not just one metric
- Consider context: winter months typically have higher activity

Return your analysis as a JSON object with this exact structure:
{
  "flu_level": <int 1-10>,
  "trend": "<increasing|stable|decreasing|rapid_increase|rapid_decrease>",
  "ili_rate_per_100k": <float or null>,
  "confirmed_cases": <int or null>,
  "dominant_strain": "<strain or null>",
  "positivity_rate": <float 0-100 or null>,
  "alerts": [<list of alert strings>],
  "confidence": <float 0-1>,
  "summary": "<English summary>",
  "week_number": <int or null>,
  "report_period": "<time period or null>"
}

Only return the JSON object, no additional text."""

    def __init__(self, model: str = "gemini-2.5-flash-lite", api_key: Optional[str] = None):
        """
        Initialize the Report Analyst Agent.

        Args:
            model: Gemini model to use (default: gemini-2.0-flash-exp for fast analysis)
            api_key: Google API key (if not in environment)
        """
        super().__init__(
            name="ReportAnalyst",
            instruction=self.ANALYSIS_INSTRUCTION,
            description="Analyzes Greek EODY flu surveillance reports and extracts structured data",
            model=model,
            api_key=api_key
        )
        self.logger.info("Report Analyst Agent initialized with ADK")

    def execute(self, parsed_content: ParsedReportContent) -> FluDataExtraction:
        """
        Analyze parsed report content and extract flu data.

        Args:
            parsed_content: ParsedReportContent with extracted text

        Returns:
            FluDataExtraction with structured flu data

        Raises:
            ValueError: If analysis fails or produces invalid data
        """
        self.logger.info(f"Analyzing report: {parsed_content.filename}")
        self.logger.info(f"Input text: {parsed_content.char_count:,} characters")

        if not parsed_content.extraction_successful:
            self.logger.error("Cannot analyze - extraction was not successful")
            raise ValueError("Parsed content extraction was not successful")

        if parsed_content.char_count < 100:
            self.logger.error("Cannot analyze - text too short")
            raise ValueError("Parsed content has insufficient text")

        # Prepare prompt for Gemini
        # Use summary section if available (faster), otherwise full text (capped)
        text_to_analyze = parsed_content.summary_section or parsed_content.full_text

        # Cap at 15000 characters to avoid token limits
        if len(text_to_analyze) > 15000:
            self.logger.info("Text exceeds 15k chars, truncating...")
            text_to_analyze = text_to_analyze[:15000]

        prompt = f"""Analyze this Greek EODY flu surveillance report:

---REPORT TEXT---
{text_to_analyze}
---END REPORT---

Extract the flu data as JSON following the specified format."""

        # Call Gemini via ADK InMemoryRunner
        try:
            self.logger.info("Sending request to Gemini...")
            runner = InMemoryRunner(agent=self.agent)
            # run_debug() is async, so we need to await it
            response = asyncio.run(runner.run_debug(prompt))

            # ADK returns a response object - extract text
            response_text = self._extract_response_text(response)

            self.logger.info(f"Received response: {len(response_text)} chars")

            # Parse JSON from response
            flu_data = self._parse_json_response(response_text)

            self.logger.info("✓ Successfully extracted flu data")
            self.logger.info(f"  Flu level: {flu_data.flu_level}/10")
            self.logger.info(f"  Trend: {flu_data.trend}")
            self.logger.info(f"  Confidence: {flu_data.confidence:.0%}")

            return flu_data

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise

    def _extract_response_text(self, response) -> str:
        """
        Extract text from ADK agent response.

        ADK can return various response types, this handles them.

        Args:
            response: Response from ADK agent

        Returns:
            Extracted text content
        """
        # If response is a string, return directly
        if isinstance(response, str):
            return response

        # If response has a 'text' attribute
        if hasattr(response, 'text'):
            return response.text

        # If response has a 'content' attribute
        if hasattr(response, 'content'):
            return response.content

        # If response is dict-like
        if isinstance(response, dict):
            if 'text' in response:
                return response['text']
            elif 'content' in response:
                return response['content']

        # Fallback: convert to string
        return str(response)

    def _parse_json_response(self, response_text: str) -> FluDataExtraction:
        """
        Parse JSON from Gemini response and create FluDataExtraction.

        Args:
            response_text: Text response from Gemini

        Returns:
            FluDataExtraction object

        Raises:
            ValueError: If JSON parsing fails or data is invalid
        """
        # Extract JSON from response (may have markdown code blocks)
        json_text = self._extract_json_from_text(response_text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            self.logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Failed to parse JSON response: {e}")

        # Validate and create FluDataExtraction
        try:
            flu_data = FluDataExtraction(**data)
            return flu_data
        except Exception as e:
            self.logger.error(f"Failed to create FluDataExtraction: {e}")
            self.logger.error(f"Data received: {data}")
            raise ValueError(f"Invalid flu data structure: {e}")

    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON object from text that may contain markdown or other content.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string
        """
        # Try to find JSON in markdown code blocks first
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_block_pattern, text, re.DOTALL)
        if matches:
            return matches[0]

        # Try to find raw JSON object
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        if matches:
            # Return the longest match (most likely to be complete)
            return max(matches, key=len)

        # If no JSON found, return original text and let JSON parser fail
        return text.strip()

    def analyze_text(self, text: str, filename: str = "direct_input.txt") -> FluDataExtraction:
        """
        Convenience method to analyze text directly without ParsedReportContent.

        Args:
            text: Text to analyze
            filename: Filename for logging purposes

        Returns:
            FluDataExtraction with structured flu data
        """
        parsed_content = ParsedReportContent(
            filename=filename,
            full_text=text,
            summary_section=text[:1500] if len(text) > 1500 else text,
            page_count=1,
            extraction_method="direct",
            char_count=len(text),
            extraction_date=datetime.now(),
            extraction_successful=True
        )

        return self.execute(parsed_content)

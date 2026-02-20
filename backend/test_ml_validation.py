import json
import os

from dotenv import load_dotenv
import google.generativeai as genai


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to run this script")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Simulate your scenario: ML metadata but earth photo content
    title = "Machine Learning Linear Regression Complete Guide"
    description = "Comprehensive guide to linear regression algorithms and implementations"
    subject = "Machine Learning"
    tags = ["machine learning", "linear regression", "algorithms", "python"]
    dept = "CSE"
    unit = "3"

    # Simulate extracted text from earth photo (no ML content)
    extracted_text = """Earth Photography Collection

This document contains high-resolution photographs of Earth from space.
Images include:
- Satellite views of continents
- Ocean currents and weather patterns
- Mountain ranges and geographical features
- Urban areas and city lights at night
- Natural disasters and climate change effects

All images are captured by NASA satellites and processed for educational purposes.
No mathematical content or algorithms are included in this collection."""

    prompt = f"""You are a strict academic notes moderator and content validator.

Your job is to validate whether the note content matches the provided metadata and is academically appropriate.

METADATA TO VALIDATE AGAINST:
- Title: "{title}"
- Description: "{description}"
- Subject: "{subject}"
- Department: "{dept}"
- Unit: "{unit}"
- Tags: {tags}

Note Content to Analyze:
{extracted_text[:4500]}

CRITICAL VALIDATION RULES:
1. If content is completely unrelated to title/description/subject → MARK AS INVALID
2. If content mentions totally different topics → MARK AS INVALID
3. If content is images/graphics with no text related to metadata → MARK AS INVALID
4. If content is in wrong subject area → MARK AS INVALID
5. Content must be DIRECTLY relevant to the specified subject and tags

Return STRICT JSON ONLY (no markdown, no explanation):

{{
  "content_valid": true/false,
  "title_match": true/false,
  "description_match": true/false,
  "subject_match": true/false,
  "tags_relevance": true/false,
  "spam_score": 0-100,
  "is_spam": true/false,
  "is_relevant": true/false,
  "summary": "brief summary of content and validation results",
  "topics": ["topic1","topic2","topic3"],
  "warnings": ["specific validation warnings"],
  "validation_details": {{
    "title_analysis": "how well content matches title",
    "description_analysis": "how well content matches description", 
    "subject_analysis": "how well content matches subject",
    "tags_analysis": "how well content aligns with tags",
    "overall_assessment": "overall content quality and relevance"
  }},
  "critical_issues": ["list of critical validation failures"]
}}

BE STRICT: If someone uploads "earth photo" but metadata says "machine learning linear regression", this MUST be marked as INVALID with clear warnings.
"""

    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        critical_issues = result.get("critical_issues", [])
        has_critical_issues = len(critical_issues) > 0

        validation_success = (
            result.get("content_valid", False)
            and result.get("title_match", False)
            and result.get("subject_match", False)
            and not result.get("is_spam", True)
            and result.get("spam_score", 100) < 50
            and not has_critical_issues
        )

        if has_critical_issues:
            validation_message = f"INVALID: {'; '.join(critical_issues[:2])}"
        elif validation_success:
            validation_message = "VALID: Content matches metadata perfectly"
        else:
            validation_message = "NEEDS REVIEW: Some validation checks failed"

        print("=== AI VALIDATION RESULTS ===")
        print(f"Validation Success: {validation_success}")
        print(f"Validation Message: {validation_message}")
        print(f"Critical Issues: {critical_issues}")
        print(f"Content Valid: {result.get('content_valid', False)}")
        print(f"Title Match: {result.get('title_match', False)}")
        print(f"Subject Match: {result.get('subject_match', False)}")
        print(f"Tags Relevance: {result.get('tags_relevance', False)}")
        print(f"Summary: {result.get('summary', '')}")
    except Exception as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()

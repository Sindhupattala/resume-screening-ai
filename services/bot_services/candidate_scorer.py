import json
from typing import Dict
import re
 
class Candidate:
    @staticmethod
    def analyze_candidate(qa_chain, query: str, candidate_name: str, resume_text: str) -> Dict[str, float]:
        """Analyze a single candidate and return a matching score."""
 
        qa_template = f"""
You are an expert resume evaluator. Your task is to score a candidate's resume against a job description with 100% accuracy and consistency.
 
**CRITICAL INSTRUCTIONS:**
1. Read the ENTIRE resume text carefully before scoring
2. Extract information ONLY from what is explicitly written
3. Follow the scoring logic exactly as specified
4. Be consistent - same input must always produce same output
5. Provide detailed explanations for transparency
6. NEVER hallucinate or make up information not in the resume
 
**JOB DESCRIPTION:**
{query}
 
**CANDIDATE RESUME:**
{resume_text}
 
**CANDIDATE NAME:** {candidate_name}
 
---
 
**SCORING BREAKDOWN (Total: 100 points)**
 
**1. MANDATORY SKILLS SCORING (0-50 points)**
 
STEP 1: Extract ALL technical skills from the Job Description
- Look for programming languages, frameworks, tools, technologies
- Include specific software, platforms, databases, cloud services
- Exclude soft skills, general terms, or behavioral traits
- For compound phrases like "implement workflows (Risk Assessment, Risk validation)", treat as ONE skill
 
STEP 2: Count extracted technical skills
- Let N = total number of technical mandatory skills from JD
- Each skill weight = 50 ÷ N points
 
STEP 3: Match skills in resume
- EXACT match or clear synonym (e.g., "Google Cloud Platform" = "GCP" = "Google Cloud")
- Must be mentioned as actual experience/skill, not just "learning" or "interested in"
- Context must clearly indicate hands-on experience
 
STEP 4: Calculate score
- Score = (Number of matched skills ÷ Total JD skills) × 50
- NO ROUNDING - use exact decimal value
 
**2. EXPERIENCE SCORING (0-30 points) - ENHANCED STRICT CALCULATION**
 
**2.1 TOTAL EXPERIENCE SCORING (0-10 points)**
 
STEP 1: Extract ALL employment periods from resume with STRICT parsing
- Look for date ranges in formats: "Jan 2022 - May 2023", "2021-Present", "Working since 2023", "2019-2022", "Jan 2020 to Dec 2022"
- Handle variations: "Current", "Present", "Till Date", "Ongoing" (assume current date as July 2025)
- Extract internships, full-time roles, contract work, freelance work
- Ignore education periods unless specifically mentioned as work experience
 
STEP 2: Convert dates to standardized format and calculate duration - CRITICAL DATE CALCULATION RULES
- Convert all dates to MM/YYYY format
- For "Present"/"Current": use 07/2025 as end date
- For year-only formats (e.g., "2019-2022"): assume Jan to Dec of respective years
- **CRITICAL**: Calculate each period duration in months using this formula:
  Duration = (End Year - Start Year) × 12 + (End Month - Start Month) + 1
  Example: Dec 2023 - Jan 2025 = (2025-2023) × 12 + (1-12) + 1 = 24 - 11 + 1 = 14 months
  Example: Jan 2022 - Dec 2022 = (2022-2022) × 12 + (12-1) + 1 = 0 + 11 + 1 = 12 months
 
STEP 3: Handle overlapping periods and gaps
- If periods overlap (e.g., "2019-2022" and "2022-2024"), merge overlapping portions
- Sort all periods chronologically
- Merge overlapping periods to avoid double counting
- Calculate total unique months of experience
 
STEP 4: Calculate total years
- Total years = Total unique months ÷ 12
- NO ROUNDING - use exact decimal value
 
STEP 5: Extract JD experience requirement
- Look for phrases like "3-8 years", "3+ years", "minimum 3 years", "5 years of experience"
- Identify the minimum required experience
- If range given (e.g., "3-5 years"), use the minimum value
 
STEP 6: Binary scoring with detailed justification
- If candidate total experience ≥ JD minimum requirement: 10 points
- If candidate total experience < JD minimum requirement: 0 points
- Show complete calculation: "Total months: X, Total years: Y.YY, JD requirement: Z years"
 
**2.2 RELEVANT EXPERIENCE SCORING (0-20 points)**
 
STEP 1: Extract relevant employment periods
- Identify roles explicitly mentioning technologies, tools, or domains listed in the JD
- Look for job titles, responsibilities, or projects that align with JD requirements
- Extract date ranges for these relevant roles using the same strict parsing as Total Experience
 
STEP 2: Calculate relevant experience duration
- Use the same date conversion and overlap handling as Total Experience
- **CRITICAL**: Use the same formula: Duration = (End Year - Start Year) × 12 + (End Month - Start Month) + 1
- Calculate total unique months of relevant experience
- Convert to years: Relevant years = Total unique relevant months ÷ 12 (NO ROUNDING)
 
STEP 3: Apply relevant experience scoring logic
- If JD requires ≤ 4 years:
  - If candidate relevant experience ≥ (JD minimum requirement - 1): 20 points
  - Else: 0 points
- If JD requires > 4 years:
  - If candidate relevant experience ≥ (JD minimum requirement - 2): 20 points
  - Else: 0 points
- Examples:
  - JD requires 3 years, candidate has 2 years relevant: 20 points (2 ≥ 3-1)
  - JD requires 5 years, candidate has 3 years relevant: 20 points (3 ≥ 5-2)
  - JD requires 6 years, candidate has 4 years relevant: 20 points (4 ≥ 6-2)
  - JD requires 3 years, candidate has 1.5 years relevant: 0 points (1.5 < 3-1)
- Show complete calculation: "Relevant months: X, Relevant years: Y.YY, JD requirement: Z years, Threshold: W years"
 
**2.3 TOTAL EXPERIENCE SCORE**
- Sum of Total Experience (0 or 10) and Relevant Experience (0 or 20) = 0-30 points
 
**3. PROJECT EXPOSURE SCORING (0-20 points)**
 
STEP 1: Identify project sections in resume
- Look for "Projects", "Key Projects", "Notable Work", "Professional Projects"
- Extract project names and descriptions
- Include work-related projects mentioned in experience section
 
STEP 2: Classify projects with strict criteria
- End-to-End (E2E): Complete projects showing full development lifecycle (design, development, testing, deployment)
- Support: Maintenance, monitoring, bug fixes, enhancements, support activities
- Academic/Unrelated: College projects, personal projects, irrelevant domain projects
 
STEP 3: Evaluate relevance to JD
- Projects must align with job requirements and domain
- Look for action verbs: built, developed, deployed, automated, implemented, designed, architected
- Check for relevant technologies, tools, and methodologies mentioned in JD
 
STEP 4: Score assignment with justification
- 20 points: At least one relevant E2E project that aligns with JD requirements
- 10 points: Only support/maintenance projects relevant to JD
- 0 points: Only academic or unrelated projects
 
---
 
**OUTPUT REQUIREMENTS:**
 
You must return ONLY a valid JSON object with this exact structure:
 
{{
  "individual_scores": {{
    "Mandatory Skills": "<exact_score>/50. JD Skills: [<complete_list_of_JD_technical_skills>]. Matched: [<list_of_matched_skills_with_evidence>]. Missing: [<list_of_missing_skills>]. ",
    "Total Experience": "<exact_score>/10. Employment periods: [<list_all_extracted_periods_with_months>]. Total months after overlap removal: <X> months = <Y.YY> years. JD requirement: <Z> years.",
    "Relevant Experience": "<exact_score>/20. Relevant periods: [<list_relevant_periods_with_months>]. Relevant months after overlap removal: <X> months = <Y.YY> years. JD requirement: <Z> years. Threshold: <W> years.",
    "Project Exposure": "<exact_score>/20. E2E projects: [<project_names_with_brief_relevance>]. Support projects: [<project_names>]. Academic/Unrelated: [<project_names>]. Scoring logic: <detailed_explanation>"
  }},
  "rating": <sum_of_all_four_scores>,
  "reason": "<comprehensive_summary_with_total_and_relevant_experience_in_readable_format>",
  "shortlisted": <boolean>  // True if Mandatory Skills score >= 30, False otherwise
}}
 
**REASON FIELD REQUIREMENTS:**
The "reason" field must provide a comprehensive summary in this format:
- **Total Experience**: Convert total months to "X years Y months" format (e.g., 53 months = "4 years 5 months")
- **Relevant Experience**: Convert relevant months to "X years Y months" format (e.g., 25 months = "2 years 1 month")
- **Domain/Technology Focus**: Mention the specific domain or technologies the candidate has worked on
- **Key Strengths**: Highlight matched skills and relevant projects
- **Gaps**: Mention missing critical skills or experience shortfalls
- **Overall Assessment**: Brief conclusion about candidate fit
 
Example reason format:
"Candidate has 4 years 5 months of total experience with 2 years 1 month of relevant experience in cloud technologies and DevOps. Strong background in Python, AWS, and Docker with hands-on experience in CI/CD pipelines. Led 2 end-to-end projects involving microservices architecture. However, lacks experience in Kubernetes and React which are critical for this role. Overall, a solid mid-level candidate with good technical foundation but some skill gaps."
 
**VALIDATION CHECKLIST:**
- [ ] All technical skills from JD identified and counted
- [ ] All employment periods extracted with exact date ranges
- [ ] Total and Relevant Experience calculations show step-by-step math with overlap handling
- [ ] **CRITICAL**: Date calculations use correct formula: (End Year - Start Year) × 12 + (End Month - Start Month) + 1
- [ ] Projects categorized with clear relevance justification
- [ ] All scores add up to final rating
- [ ] Explanations include specific evidence from resume
- [ ] NO HALLUCINATION - only use information explicitly stated in resume
 
**CRITICAL EXPERIENCE CALCULATION RULES:**
1. ALWAYS show the raw extracted periods first
2. ALWAYS convert to months for precise calculation using the correct formula
3. ALWAYS handle overlaps by merging periods
4. ALWAYS show final calculation: months → years → comparison with JD
5. NEVER round experience years prematurely
6. ALWAYS use binary scoring for Total Experience (10 or 0) and Relevant Experience (20 or 0)
7. **CRITICAL**: Dec 2023 - Jan 2025 = 14 months (not 1 month)
 
**EXAMPLE DETAILED CALCULATIONS:**
- Mandatory Skills: JD has ["Python", "AWS", "Docker", "Kubernetes", "React"] = 5 skills. Resume has ["Python", "AWS", "Docker"] = 3 skills. Score: 3/5 × 50 = 30.0/50
- Total Experience:
  * Period 1: "Jan 2019 - Dec 2021" = (2021-2019) × 12 + (12-1) + 1 = 36 months
  * Period 2: "Jun 2021 - Present (July 2025)" = (2025-2021) × 12 + (7-6) + 1 = 50 months
  * Overlap: Jun 2021 - Dec 2021 = 7 months
  * Total: 36 + 50 - 7 = 79 months = 6.58 years
  * JD requires 3+ years → 6.58 ≥ 3 → 10/10 points
- Relevant Experience:
  * Relevant Period: "Jun 2021 - Present (July 2025)" = 50 months = 4.17 years
  * JD requires 5 years → Threshold: 5-2 = 3 years → 4.17 ≥ 3 → 20/20 points
- Projects: 1 E2E project relevant to JD → 20/20 points
- Final Rating: 30 + 10 + 20 + 20 = 80/100
 
**EXAMPLE REASON FORMAT:**
"Candidate has 6 years 7 months of total experience with 4 years 2 months of relevant experience in software development and cloud technologies. Strong proficiency in Python, AWS, and Docker with hands-on experience in building scalable applications. Successfully delivered 1 end-to-end project involving microservices deployment. However, missing critical skills in Kubernetes and React which are essential for this role. Overall, an experienced developer with solid technical foundation but some key skill gaps that may require additional training."
 
Now analyze the candidate with maximum precision and strictness:
"""
 
        try:
            response = qa_chain.invoke({"query": qa_template})
            result = response.get('result') if isinstance(response, dict) else response
            result = result.strip().replace("```json", "").replace("```", "").strip()
 
            try:
                result_json = json.loads(result)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return {
                    "rating": 0.0,
                    "reason": "Invalid JSON response from QA chain",
                    "individual_scores": {},
                    "shortlisted": False
                }
 
            def extract_score(score_string: str) -> float:
                try:
                    match = re.match(r"(\d+(\.\d+)?)/\d+", score_string.strip())
                    if not match:
                        print(f"Invalid score format: {score_string}")
                        return 0.0
                    return float(match.group(1))
                except (AttributeError, ValueError) as e:
                    print(f"Error parsing score: {e}")
                    return 0.0
 
            individual_scores = result_json.get("individual_scores", {})
 
            # Extract scores with correct keys
            mandatory_score = extract_score(individual_scores.get("Mandatory Skills", "0.0/50"))
            total_experience_score = extract_score(individual_scores.get("Total Experience", "0.0/10"))
            relevant_experience_score = extract_score(individual_scores.get("Relevant Experience", "0.0/20"))
            project_score = extract_score(individual_scores.get("Project Exposure", "0.0/20"))
 
            # Sum and clamp the total score
            score = mandatory_score + total_experience_score + relevant_experience_score + project_score
            score = min(100.0, max(0.0, score))
 
            # Shortlist candidates with Mandatory Skills score >= 30
            shortlisted = mandatory_score >= 30.0
 
            return {
                "rating": score,
                "reason": result_json.get("reason", "No reason provided"),
                "individual_scores": individual_scores,
                "shortlisted": shortlisted
            }
 
        except Exception as e:
            print(f"Unexpected error in candidate analysis: {e}")
            return {
                "rating": 0.0,
                "reason": f"Error processing candidate: {str(e)}",
                "individual_scores": {},
                "shortlisted": False
            }
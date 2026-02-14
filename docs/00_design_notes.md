# Design Notes (Phase 0)

## Fact table grain
**fact_enrolment grain:** One row per student per academic year per programme enrolment (including study mode).

## Core analytical questions
- How has total enrolment changed over 6 academic years?
- How do trends vary by faculty and programme?
- What is YoY growth by year and programme?
- What is retention rate by faculty/programme/mode?
- What is projected enrolment for the next 3 years?
- Which cohorts show elevated progression risk?

## Core KPIs (minimum)
1. **Total Enrolment (Headcount)** = COUNT(DISTINCT student_key) for a given academic_year.
2. **YoY Growth %** = (Enrolment_t - Enrolment_t-1) / Enrolment_t-1.
3. **Retention Rate** = % of students in year T who are also enrolled in year T+1.
4. **UG vs PG Split** = enrolment by programme_level.
5. **FT vs PT Split** = enrolment by study_mode.

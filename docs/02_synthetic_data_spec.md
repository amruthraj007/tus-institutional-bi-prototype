# Synthetic Data Spec

## Target shape
- Academic years: 6
- Faculties: 4
- Programmes: 12–16
- Students: ~8,000 unique
- Fact rows: ~18k–30k

## Dimension values
- Faculties: Business, Engineering, Science, Arts & Social
- Study modes: FT, PT
- Programme levels: UG, PG
- Age bands: <=20, 21–24, 25–34, 35+
- Gender: M/F (or include Non-binary if desired)
- Entry types (optional): Standard, Transfer, International

## Fact generation rules (high level)
- Create programme-year enrolment targets using baseline sizes + growth/decline patterns.
- Assign students to programme/year; set study_mode probabilities by level.
- Maintain year_of_study progression for returning students.
- Generate retained_next_year_flag and progressed_next_year_flag using baseline probabilities + small adjustments:
  - PT slightly lower retention/progression
  - Older age bands slightly lower
  - Programme-level effects (some stronger/weaker)
- Enforce constraints:
  - No duplicate rows at grain
  - progressed_next_year_flag should not exceed retention logic
  - All foreign keys valid

## Intended “ground truth” patterns
- Overall enrolment gradual growth (~2%/year)
- One faculty grows, one slightly declines
- PG share gradually increases
- Retention lower for PT and older age bands

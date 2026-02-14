# Schema Specification (Star Schema)

## Dimensions

### dim_time
- time_key (PK)
- academic_year (e.g., 2019/20)

### dim_faculty
- faculty_key (PK)
- faculty_name

### dim_programme
- programme_key (PK)
- programme_name
- programme_level (UG/PG)
- faculty_key (FK → dim_faculty)

### dim_mode
- mode_key (PK)
- study_mode (FT/PT)

### dim_student
- student_key (PK)
- gender
- age_band
- entry_type (optional)

## Fact

### fact_enrolment (grain: student × year × programme × mode)
- student_key (FK)
- programme_key (FK)
- time_key (FK)
- mode_key (FK)
- year_of_study
- enrolled_flag
- retained_next_year_flag (recommended)
- progressed_next_year_flag

## KPI mapping
- Total Enrolment: fact_enrolment + dim_time
- YoY Growth: Total Enrolment with year lag
- Retention Rate: retained_next_year_flag (or derived across years)
- UG/PG Split: join dim_programme
- FT/PT Split: join dim_mode

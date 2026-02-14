import os
import random
from dataclasses import dataclass
from datetime import date
import numpy as np
import pandas as pd
import duckdb

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Paths
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WAREHOUSE_DIR = os.path.join(REPO_ROOT, "warehouse")
DB_PATH = os.path.join(WAREHOUSE_DIR, "tus.duckdb")
RAW_DIR = os.path.join(REPO_ROOT, "data", "raw")

os.makedirs(WAREHOUSE_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

@dataclass
class ProgrammeSpec:
    faculty_name: str
    programme_name: str
    programme_level: str  # UG/PG
    baseline_size: int
    trend: float  # e.g., +0.03 growth or -0.02 decline

def academic_years(start_year: int, n: int) -> list[str]:
    # e.g., 2019/20
    return [f"{y}/{str(y+1)[-2:]}" for y in range(start_year, start_year + n)]

def make_dimensions() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Faculties
    faculties = ["Business", "Engineering", "Science", "Arts & Social"]
    dim_faculty = pd.DataFrame({
        "faculty_key": range(1, len(faculties) + 1),
        "faculty_name": faculties
    })

    # Time (6 years)
    years = academic_years(2019, 6)
    dim_time = pd.DataFrame({
        "time_key": range(1, len(years) + 1),
        "academic_year": years
    })

    # Mode
    dim_mode = pd.DataFrame({
        "mode_key": [1, 2],
        "study_mode": ["FT", "PT"]
    })

    # Programmes: 12 (3 per faculty)
    programme_specs = [
        ProgrammeSpec("Business", "BSc Accounting", "UG", 320, 0.02),
        ProgrammeSpec("Business", "BA Marketing", "UG", 260, 0.01),
        ProgrammeSpec("Business", "MSc Business Analytics", "PG", 120, 0.04),

        ProgrammeSpec("Engineering", "BEng Mechanical", "UG", 300, 0.01),
        ProgrammeSpec("Engineering", "BEng Software", "UG", 340, 0.03),
        ProgrammeSpec("Engineering", "MEng Renewable Energy", "PG", 80, 0.02),

        ProgrammeSpec("Science", "BSc Biology", "UG", 240, -0.01),
        ProgrammeSpec("Science", "BSc Data Science", "UG", 280, 0.05),
        ProgrammeSpec("Science", "MSc Applied AI", "PG", 100, 0.04),

        ProgrammeSpec("Arts & Social", "BA Psychology", "UG", 260, 0.02),
        ProgrammeSpec("Arts & Social", "BA Social Care", "UG", 220, -0.01),
        ProgrammeSpec("Arts & Social", "MA Education", "PG", 90, 0.01),
    ]

    fac_key_map = dict(zip(dim_faculty["faculty_name"], dim_faculty["faculty_key"]))

    dim_programme = pd.DataFrame({
        "programme_key": range(1, len(programme_specs) + 1),
        "programme_name": [p.programme_name for p in programme_specs],
        "programme_level": [p.programme_level for p in programme_specs],
        "faculty_key": [fac_key_map[p.faculty_name] for p in programme_specs],
        "baseline_size": [p.baseline_size for p in programme_specs],
        "trend": [p.trend for p in programme_specs],
    })

    # Students: ~8000 unique students with demographics
    n_students = 8000
    genders = ["F", "M"]
    age_bands = ["<=20", "21-24", "25-34", "35+"]
    entry_types = ["Standard", "Transfer", "International"]

    dim_student = pd.DataFrame({
        "student_key": range(1, n_students + 1),
        "gender": np.random.choice(genders, size=n_students, p=[0.52, 0.48]),
        "age_band": np.random.choice(age_bands, size=n_students, p=[0.45, 0.30, 0.18, 0.07]),
        "entry_type": np.random.choice(entry_types, size=n_students, p=[0.82, 0.10, 0.08]),
    })

    return dim_faculty, dim_time, dim_mode, dim_programme, dim_student

def generate_fact_enrolment(dim_time, dim_mode, dim_programme, dim_student) -> pd.DataFrame:
    years = dim_time.sort_values("time_key")[["time_key", "academic_year"]].to_records(index=False)
    students = dim_student["student_key"].tolist()

    # Track student "state" so year_of_study can increment if retained
    # Key: (student_key, programme_key) -> last_time_key, last_year_of_study
    state = {}

    rows = []
    noise_sd = 0.07  # controls variability per programme-year

    for time_key, academic_year in years:
        year_index = time_key - 1  # 0..5

        for _, prog in dim_programme.iterrows():
            programme_key = int(prog["programme_key"])
            level = prog["programme_level"]
            baseline = int(prog["baseline_size"])
            trend = float(prog["trend"])

            # target size with trend + mild overall growth
            overall_growth = 0.02
            target = baseline * ((1 + overall_growth + trend) ** year_index)

            # add noise
            target = int(max(20, np.random.normal(target, target * noise_sd)))

            # sample students for this programme-year
            sampled_students = np.random.choice(students, size=target, replace=False)

            # mode probability based on level
            if level == "UG":
                mode_probs = {"FT": 0.80, "PT": 0.20}
                max_year = 4
                base_ret = 0.80
                base_prog = 0.78
            else:
                mode_probs = {"FT": 0.45, "PT": 0.55}
                max_year = 2
                base_ret = 0.75
                base_prog = 0.73

            for student_key in sampled_students:
                # assign mode
                study_mode = np.random.choice(["FT", "PT"], p=[mode_probs["FT"], mode_probs["PT"]])
                mode_key = 1 if study_mode == "FT" else 2

                # determine year_of_study based on whether student was previously in same programme
                key = (int(student_key), programme_key)
                if key in state and state[key]["last_time_key"] == time_key - 1:
                    year_of_study = min(state[key]["last_year_of_study"] + 1, max_year)
                else:
                    year_of_study = 1

                # demographic adjustments
                stu = dim_student.loc[dim_student["student_key"] == student_key].iloc[0]
                age_band = stu["age_band"]
                entry_type = stu["entry_type"]

                adj = 0.0
                if study_mode == "PT":
                    adj -= 0.05
                if age_band == "35+":
                    adj -= 0.03
                if entry_type == "Transfer":
                    adj -= 0.02

                # programme effect (small, stable)
                prog_effect = np.random.normal(0.0, 0.01)
                p_ret = np.clip(base_ret + adj + prog_effect, 0.40, 0.95)
                p_prog = np.clip(base_prog + adj + prog_effect, 0.35, 0.95)

                retained_next_year_flag = 1 if np.random.rand() < p_ret else 0

                # Progression generally implies retention; keep consistent
                progressed_next_year_flag = 1 if (retained_next_year_flag == 1 and np.random.rand() < p_prog) else 0

                rows.append({
                    "student_key": int(student_key),
                    "programme_key": programme_key,
                    "time_key": int(time_key),
                    "mode_key": int(mode_key),
                    "year_of_study": int(year_of_study),
                    "enrolled_flag": 1,
                    "retained_next_year_flag": int(retained_next_year_flag),
                    "progressed_next_year_flag": int(progressed_next_year_flag),
                })

                # update state for next year's year_of_study logic
                state[key] = {
                    "last_time_key": int(time_key),
                    "last_year_of_study": int(year_of_study),
                }

    fact = pd.DataFrame(rows)

    # Enforce grain uniqueness
    fact = fact.drop_duplicates(subset=["student_key", "programme_key", "time_key", "mode_key"])
    return fact

def write_to_duckdb(dim_faculty, dim_time, dim_mode, dim_programme, dim_student, fact_enrolment):
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")

    # Load tables into raw schema
    con.register("df_faculty", dim_faculty)
    con.register("df_time", dim_time)
    con.register("df_mode", dim_mode)
    con.register("df_programme", dim_programme.drop(columns=["baseline_size", "trend"]))
    con.register("df_student", dim_student)
    con.register("df_fact", fact_enrolment)

    con.execute("DROP TABLE IF EXISTS raw.faculty;")
    con.execute("DROP TABLE IF EXISTS raw.time;")
    con.execute("DROP TABLE IF EXISTS raw.mode;")
    con.execute("DROP TABLE IF EXISTS raw.programme;")
    con.execute("DROP TABLE IF EXISTS raw.student;")
    con.execute("DROP TABLE IF EXISTS raw.enrolment;")

    con.execute("CREATE TABLE raw.faculty AS SELECT * FROM df_faculty;")
    con.execute("CREATE TABLE raw.time AS SELECT * FROM df_time;")
    con.execute("CREATE TABLE raw.mode AS SELECT * FROM df_mode;")
    con.execute("CREATE TABLE raw.programme AS SELECT * FROM df_programme;")
    con.execute("CREATE TABLE raw.student AS SELECT * FROM df_student;")
    con.execute("CREATE TABLE raw.enrolment AS SELECT * FROM df_fact;")

    # Basic sanity checks
    counts = con.execute("""
        SELECT
          (SELECT COUNT(*) FROM raw.student) AS students,
          (SELECT COUNT(*) FROM raw.programme) AS programmes,
          (SELECT COUNT(*) FROM raw.enrolment) AS enrolment_rows
    """).fetchall()[0]

    con.close()
    return counts

def main():
    dim_faculty, dim_time, dim_mode, dim_programme, dim_student = make_dimensions()
    fact_enrolment = generate_fact_enrolment(dim_time, dim_mode, dim_programme, dim_student)

    # Also write small CSVs for transparency (optional)
    dim_faculty.to_csv(os.path.join(RAW_DIR, "faculty.csv"), index=False)
    dim_time.to_csv(os.path.join(RAW_DIR, "time.csv"), index=False)
    dim_mode.to_csv(os.path.join(RAW_DIR, "mode.csv"), index=False)
    dim_programme.drop(columns=["baseline_size", "trend"]).to_csv(os.path.join(RAW_DIR, "programme.csv"), index=False)
    dim_student.to_csv(os.path.join(RAW_DIR, "student.csv"), index=False)
    fact_enrolment.to_csv(os.path.join(RAW_DIR, "enrolment.csv"), index=False)

    students, programmes, enrol_rows = write_to_duckdb(
        dim_faculty, dim_time, dim_mode,
        dim_programme, dim_student, fact_enrolment
    )

    print("✅ Synthetic data generated and loaded to DuckDB")
    print(f"Students: {students:,}")
    print(f"Programmes: {programmes:,}")
    print(f"Enrolment rows: {enrol_rows:,}")
    print(f"DuckDB path: {DB_PATH}")

if __name__ == "__main__":
    main()

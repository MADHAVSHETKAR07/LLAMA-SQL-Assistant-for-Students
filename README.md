# LLaMA SQL Assistant

A Streamlit web app that lets you query a student marks database using plain English. Type a question, and the app uses Groq's LLaMA 3.1 model to generate a safe MySQL `SELECT` query, runs it against a MySQL database, displays the results, explains the query in simple terms, and lets you visualize the data with bar charts, pie charts, and histograms.

## Features

- **Natural language to SQL** — Ask questions like "show marks for first sem" and get a valid MySQL query.
- **Safe query generation** — Only `SELECT` statements are allowed. Any query containing `DELETE`, `UPDATE`, `INSERT`, `DROP`, `TRUNCATE`, or `ALTER` is blocked and replaced with a safe fallback query.
- **Forced schema/join structure** — Generated queries are rebuilt around a fixed `SELECT` column list and `JOIN` structure to prevent malformed or unintended queries.
- **Semester keyword detection** — Phrases like "first sem", "2nd sem", etc. are automatically mapped to the correct `sub.semester` filter, even if the LLM misses it.
- **Automatic row limiting** — A `LIMIT 100` is added if the generated query doesn't already have one.
- **Plain-English query explanation** — The generated SQL is explained step by step using LLaMA, shown in an expandable section.
- **Data visualization** — Once results are returned, you can generate:
  - Bar chart of average marks per subject
  - Pie chart of marks distribution by subject
  - Histogram of any numeric column

## Database Schema

The app expects a MySQL database (default name: `mgm2`) with the following tables:

**students**
- `student_id`
- `student_name`
- `admission_year`

**subjects**
- `subject_id`
- `subject_name`
- `class_year`
- `semester`
- `is_practical`

**marks**
- `mark_id`
- `student_id`
- `subject_id`
- `academic_year`
- `marks`

**Relationships**
- `students.student_id = marks.student_id`
- `marks.subject_id = subjects.subject_id`

## Requirements

- Python 3.9+
- MySQL Server with the `mgm2` database (schema above) populated with data
- A [Groq](https://console.groq.com/) API key

### Python Packages

```
streamlit
mysql-connector-python
pandas
groq
python-dotenv
matplotlib
seaborn
```

## Setup

1. **Clone or download this project.**

2. **Install dependencies:**

   ```bash
   pip install streamlit mysql-connector-python pandas groq python-dotenv matplotlib seaborn
   ```

3. **Set up the MySQL database.**

   Create a database named `mgm2` (or update the connection settings in `read_sql_query()` in `main.py`) with the `students`, `subjects`, and `marks` tables described above.

4. **Configure environment variables.**

   Create a `.env` file in the project root:

   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Update MySQL connection settings if needed.**

   By default, the app connects with:

   ```python
   host="localhost"
   user="root"
   password=""
   database="mgm2"
   ```

   Edit these values in `main.py` to match your local MySQL setup.

## Running the App

```bash
streamlit run main.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`) in your browser.

## Usage

1. Type a question in plain English, e.g.:
   - "Show all marks for first sem"
   - "Average marks in second year students"
   - "List marks for subject Mathematics"
2. Click **Run**.
3. View the generated SQL, the resulting data table, and an expandable plain-English explanation of the query.
4. Use the checkboxes under **Visualizations** to generate a bar chart, pie chart, or histogram from the results.

## How It Works

1. The user's question is sent to Groq's `llama-3.1-8b-instant` model along with a system prompt describing the database schema and query rules.
2. The raw SQL returned by the model is cleaned (code fences stripped) and checked for forbidden keywords or non-`SELECT` statements.
3. If the query passes safety checks, any `WHERE`, `GROUP BY`, or `ORDER BY` clause is extracted and reattached to a fixed, known-safe `SELECT ... FROM ... JOIN ...` structure, with table references normalized to the correct aliases (`s`, `m`, `sub`).
4. Semester-related keywords in the question are cross-checked against a keyword map and added to the `WHERE` clause if not already present.
5. A `LIMIT 100` is appended if missing, and the final query is executed against MySQL.
6. Results are shown in a table, explained via a second LLaMA call, and made available for charting.

## Notes / Limitations

- The app currently supports only read-only (`SELECT`) queries by design.
- Query generation and explanation depend on the Groq API being reachable and the API key being valid.
- MySQL credentials are hardcoded in `main.py`; consider moving them to environment variables for better security.
- Charting functions (`create_bar_chart`, `create_pie_chart`) expect `subject_name` and `marks` columns to be present in the result set.
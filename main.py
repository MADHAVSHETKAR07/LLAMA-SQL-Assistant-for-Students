import streamlit as st
import mysql.connector
import pandas as pd
from groq import Groq
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns

# ================= LOAD ENV ====================
load_dotenv()
llama_key = os.getenv("GROQ_API_KEY")

# ================= LLaMA CLIENT =================
client = Groq(api_key=llama_key)

# ================= BASE JOIN ====================
BASE_JOIN = """
FROM students s
JOIN marks m ON s.student_id = m.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id
"""

SAFE_SELECT = """
SELECT 
    s.student_id,
    s.student_name,
    sub.subject_name,
    m.marks
"""

PROMPT = """
You are a professional MySQL developer.

Convert the user question into a valid MySQL SELECT query.

DATABASE SCHEMA

students
- student_id
- student_name
- admission_year

subjects
- subject_id
- subject_name
- class_year
- semester
- is_practical

marks
- mark_id
- student_id
- subject_id
- academic_year
- marks

RELATIONSHIPS

students.student_id = marks.student_id
marks.subject_id = subjects.subject_id

IMPORTANT RULES

1. Use table aliases:
   students = s
   marks = m
   subjects = sub

2. Always JOIN tables like this:

FROM students s
JOIN marks m ON s.student_id = m.student_id
JOIN subjects sub ON m.subject_id = sub.subject_id

3. Semester information comes ONLY from subjects table

Example mappings:
- first sem → sub.semester = 1
- second sem → sub.semester = 2
- third sem → sub.semester = 3
- fourth sem → sub.semester = 4
- fifth sem → sub.semester = 5
- sixth sem → sub.semester = 6

4. If question asks:
"first year student"
→ sub.class_year = 1

5. If question asks:
"second year student"
→ sub.class_year = 2

6. Always return columns:

SELECT
s.student_id,
s.student_name,
sub.subject_name,
m.marks

7. Only generate SELECT queries.

Return ONLY SQL.
"""

# ================= SAFE SQL GENERATOR ====================
def get_llama_sql(question, prompt):

    full_prompt = (
        prompt
        + "\nUSER QUESTION:\n"
        + question
        + "\n\nReturn ONLY valid MySQL SELECT query."
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0
    )

    raw = response.choices[0].message.content
    raw = raw.replace("```sql", "").replace("```", "").strip()
    sql = raw.split(";")[0].strip()
    sql_lower = sql.lower()
    
    # Detect semester keywords
    semester_map = {
        "first sem": "sub.semester = 1",
        "1st sem": "sub.semester = 1",
        "second sem": "sub.semester = 2",
        "2nd sem": "sub.semester = 2",
        "third sem": "sub.semester = 3",
        "3rd sem": "sub.semester = 3",
        "fourth sem": "sub.semester = 4",
        "4th sem": "sub.semester = 4",
        "fifth sem": "sub.semester = 5",
        "5th sem": "sub.semester = 5",
        "sixth sem": "sub.semester = 6",
        "6th sem": "sub.semester = 6",
    }

    extra_semester = ""

    for key in semester_map:
        if key in question.lower():
            extra_semester = semester_map[key]
            break

    forbidden = ["delete", "update", "insert", "drop", "truncate", "alter"]

    # ❌ Block dangerous queries
    if any(word in sql_lower for word in forbidden):
        return SAFE_SELECT + BASE_JOIN + " LIMIT 100"

    # ❌ If not SELECT → safe query
    if not sql_lower.startswith("select"):
        return SAFE_SELECT + BASE_JOIN + " LIMIT 100"

        # ===============================
        # ✅ FORCE BASE JOIN STRUCTURE
        # ===============================

    extra_clause = ""

    if "where" in sql_lower:
        extra_clause = sql[sql_lower.index("where"):]
    elif "group by" in sql_lower:
        extra_clause = sql[sql_lower.index("group by"):]
    elif "order by" in sql_lower:
        extra_clause = sql[sql_lower.index("order by"):]

    # FIX alias problem
    extra_clause = extra_clause.replace("students.", "s.")
    extra_clause = extra_clause.replace("marks.", "m.")
    extra_clause = extra_clause.replace("subjects.", "sub.")

    # final_sql = SAFE_SELECT + BASE_JOIN + " " + extra_clause
    
    final_sql = SAFE_SELECT + BASE_JOIN

    if extra_clause:
        final_sql += " " + extra_clause

    if extra_semester:
        if "where" in final_sql.lower():
            final_sql += " AND " + extra_semester
        else:
            final_sql += " WHERE " + extra_semester

    if "limit" not in final_sql.lower():
        final_sql += " LIMIT 100"

    return final_sql.strip()

# ================= MYSQL =======================
def read_sql_query(sql):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="mgm2"
        )
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        conn.close()
        return rows, cols
    except mysql.connector.Error as e:
        return [("SQL Error", str(e))], ["Type", "Message"]


# ================= CHARTS ======================
def create_histogram(df, column):
    '''skip student_id and student_name'''
    plt.figure(figsize=(10, 6))
    sns.histplot(df[column], bins=20, kde=True)
    plt.title(f"Histogram of {column}")
    st.pyplot(plt)


# ================= CHARTS ======================

def create_bar_chart(df):
    if "subject_name" in df.columns and "marks" in df.columns:

        chart_data = df.groupby("subject_name")["marks"].mean().reset_index()

        plt.figure(figsize=(10,6))
        sns.barplot(x="subject_name", y="marks", data=chart_data)

        plt.xlabel("Subject")
        plt.ylabel("Marks")
        plt.title("Average Marks per Subject")
        plt.xticks(rotation=45)

        st.pyplot(plt)

    else:
        st.warning("Required columns not found for bar chart")


def create_pie_chart(df):

    if "subject_name" in df.columns and "marks" in df.columns:

        chart_data = df.groupby("subject_name")["marks"].mean()

        total = chart_data.sum()

        def show_marks(pct):
            value = int(round(pct * total / 100.0))
            return f"{value}"

        plt.figure(figsize=(8,8))

        plt.pie(
            chart_data,
            labels=chart_data.index,
            autopct=show_marks
        )

        plt.title("Marks Distribution by Subject")

        st.pyplot(plt)

    else:
        st.warning("Required columns not found for pie chart")

# ================= EXPLAIN SQL ==================
def explain_sql_query(query):
    explain_prompt = f"""
Explain the following MySQL query step by step
in very simple words for a college student.

Query:
{query}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": explain_prompt}],
        temperature=0
    )

    return response.choices[0].message.content.strip()


# ================= STREAMLIT UI =================
st.set_page_config(page_title="LLAMA SQL Assistant")
st.title("LLAMA SQL Assistant For Student ")
st.write("Ask in English. Get SQL + Result.")

question = st.text_input("Enter your question:")

if st.button("Run"):
    if question.strip():

        sql_query = get_llama_sql(question, PROMPT)

        st.subheader("Generated SQL")
        st.code(sql_query, language="sql")

        result, columns = read_sql_query(sql_query)

        if columns == ["Type", "Message"]:
            st.error(result[0][1])
        else:
            df = pd.DataFrame(result, columns=columns)
            for c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="ignore")

            st.session_state["df"] = df
            st.dataframe(df)

        with st.expander("LLaMA Explains SQL"):
            st.write(explain_sql_query(sql_query))

    else:
        st.warning("Please enter a question.")



# ================= VISUALS =====================
if "df" in st.session_state:
    df = st.session_state["df"]

    st.subheader("Visualizations")

    if st.checkbox("Bar Chart"):
        create_bar_chart(df)

    if st.checkbox("Pie Chart"):
        create_pie_chart(df)

    if st.checkbox("Histogram"):
        num_cols = df.select_dtypes(include="number").columns
        if len(num_cols):
            col = st.selectbox("Select column", num_cols)
            create_histogram(df, col)
        else:
            st.info("No numeric columns available for histogram.")
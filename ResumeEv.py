import os
import json
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel
from pypdf import PdfReader 
from docx import Document
from pathlib import Path

load_dotenv()

my_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=my_api_key)
model = "openai/gpt-oss-120b"

job_description = """ We are looking for a Python Developer.
 Job Title: Python Developer Company: ABC Technologies Experience Required: 2+ years Required Skills: - Python - FastAPI - REST API - SQL - Git - PostgreSQL Preferred Skills: - Docker - AWS - MongoDB Education: Bachelor's degree in Computer Science, Information Technology, or related field. """

class JobDescription(BaseModel):
    job_title: str
    company: str
    experience_required: str
    required_skills: list[str]
    preferred_skills: list[str]
    education: str
    location: str | None = None

job_description_prompt = f"""
You are a job description parser. Extract the information in JSON format using EXACTLY these underscore keys:
- job_title
- company
- experience_required
- required_skills
- preferred_skills
- education
- location

Job Description: {job_description}
"""
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": job_description_prompt}],
    response_format={"type": "json_object"} 
)

job_data = JobDescription.model_validate_json(response.choices[0].message.content)
print(job_data.model_dump_json(indent=4))

def read_resume(file_path):

    file_path = str(file_path)

    text = ""
    if file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)

        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text.strip()

    if file_path.lower().endswith(".docx"):
        document = Document(file_path)

        for paragraph in document.paragraphs:   
            text += paragraph.text + "\n"

        return text.strip()

    raise ValueError("Unsupported file format. Please provide a PDF or DOCX file.")

class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

class Resume(BaseModel):
    name: str
    email: str
    phone: str | None = None
    skills: list[str] = []
    education: list[str] = []  # LLM ko hum simple list of strings bhejne ko bolenge
    experience: list[Experience] = []

resume_folder = Path("resumes")
result = []

if not resume_folder.exists(): #check if the folder exists or not
    print("Folder 'resumes' nahi mila!")
else:
    for file in resume_folder.iterdir():#in the folder iterate through all the files
        if file.suffix.lower() in ['.pdf','.docx']:#check if the file is pdf or docx
            # print(f"Processing file: {file.name}")
            resume_text = read_resume(file)
            resume_prompt = f"""
           Extract information from this resume into JSON format using EXACTLY these keys:
            - name (string)
            - email (string)
            - phone (string or null)
            - skills (list of strings)
            - education (list of plain text strings, e.g. ["Bachelor of Science in CS", "High School"])
            - experience (list of objects with keys: company, role, start_date, end_date, description)

            Resume Text:
            {resume_text}"""

            response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": resume_prompt}],response_format={"type": "json_object"},)
            resume_data = Resume.model_validate_json(response.choices[0].message.content)
            result.append(resume_data)
            print(f"Successfully Parsed:{resume_data.name}")
            print(resume_data.model_dump_json(indent=4))
        else:
            print(f"Skipping unsupported file format: {file.name}")
            continue
        

class MatchResult(BaseModel):
    match_score : int
    matching_skills: list[str]
    missing_skills:list[str]
    summary_reason:str

def compare_resume_with_jd(job_data,resume_data):
    matching_prompt=f"""
    You are an AI ATS Evaluator. Compare the Candidate Resume with the Job Description.
    JOB DESCRIPTION:
    - Title: {job_data.job_title}
    - Required Skills: {job_data.required_skills}
    - Preferred Skills: {job_data.preferred_skills}
    - Experience Required: {job_data.experience_required}
    CANDIDATE RESUME:
    - Name: {resume_data.name}
    - Skills: {resume_data.skills}
    - Experience: {resume_data.experience}
    - Education: {resume_data.education}
    
    Evaluate and return JSON with EXACT keys:
    - match_score (integer from 0 to 100 based on skill overlap and experience fit)
    - matching_skills (list of skills that match)
    - missing_skills (list of required skills missing in candidate resume)
    - summary_reason (2-3 sentences explaining why this score was given)
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": matching_prompt}],
        response_format={"type": "json_object"},
    )

    return MatchResult.model_validate_json(response.choices[0].message.content)

match_analysis=compare_resume_with_jd(job_data,resume_data)
print(match_analysis.model_dump_json(indent=4))
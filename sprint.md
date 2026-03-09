🧠 DETAILED SPRINT-WISE TASK EXECUTION GUIDE

Digital Resume Management, Weighted Scoring & AI Feedback System

🔷 SPRINT 0 — PROBLEM UNDERSTANDING & DESIGN FREEZE
🔹 Task S0-T1: Problem Understanding

Intent
Ensure the student understands why the system exists — not just what to code.

What student must do

Read synopsis carefully

Rewrite the problem in their own words

Identify pain points in manual recruitment

Key Questions to Ask

Why is manual screening inefficient?

What decisions should the system NOT make?

Common Mistakes

Jumping to AI too early

Confusing shortlisting with hiring

Output

1-page written explanation

🔹 Task S0-T2: Scope Definition

Intent
Prevent feature creep and viva confusion.

What student must do

List:

In-scope features

Out-of-scope features

In Scope

Resume upload

Scoring

Feedback

Ranking

Out of Scope

Final hiring

ML model training

Interview scheduling

Output

Scope table signed off by mentor

🔹 Task S0-T3: Actor Identification

Intent
Convert system into use-case driven design.

What student must do

Identify users

Map each action per role

Example

Job seeker → upload resume, view feedback

Recruiter → create job, view rankings

Output

Use-case diagram

🔹 Task S0-T4: Architecture Diagram

Intent
See the system end-to-end.

What student must do

Draw logical components

Show data movement

Must Include

Resume parser

Rule engine

AI feedback module

Common Mistakes

Mixing frontend and backend logic

Showing AI as decision-maker

Output

Labeled architecture diagram

🔹 Task S0-T5: Database Schema Design

Intent
Ensure structured, queryable data.

What student must do

Identify entities

Define relationships

Assign primary & foreign keys

Critical Tables

users

jobs

resumes

applications

scores

feedback

Output

ER diagram + CREATE TABLE scripts

🟢 SPRINT 1 — PROJECT SETUP & BASE PLATFORM
🔹 Task S1-T1: Development Environment Setup

Intent
Stable, repeatable development environment.

What student must do

Install Python

Create virtual environment

Install required packages

Mentor Check

No global installs

Clean pip freeze

Output

Working local server

🔹 Task S1-T2: Project Structure

Intent
Prevent a “single-file project”.

What student must do

Separate:

routes

services

db

utils

templates

Why it matters

Readability

Marks

Industry alignment

Output

Folder tree review

🔹 Task S1-T3: Database Connection

Intent
Backend ↔ DB handshake.

What student must do

Create DB config

Test connection

Handle failures gracefully

Common Mistakes

Hardcoded credentials

No error handling

Output

Test insert/select script

🔹 Task S1-T4: Static Pages

Intent
Navigation before logic.

What student must do

Create templates:

Home

Login

Register

Output

Pages accessible via routes

🟡 SPRINT 2 — AUTHENTICATION & ROLE MANAGEMENT
🔹 Task S2-T1: User Registration

Intent
Establish digital identity.

What student must do

Validate inputs

Store hashed passwords

Assign role at signup

Edge Cases

Duplicate email

Weak passwords

Output

User record in DB

🔹 Task S2-T2: Login System

Intent
Secure access control.

What student must do

Authenticate credentials

Create session

Redirect based on role

Common Mistakes

Plain-text passwords

Session leaks

Output

Successful login/logout

🔹 Task S2-T3: Role-Based Access Control

Intent
Prevent cross-role misuse.

What student must do

Decorators / middleware

Role checks per route

Output

Job seeker can’t post jobs

Recruiter can’t upload resumes

🔵 SPRINT 3 — JOB POSTING & RESUME MANAGEMENT
🔹 Task S3-T1: Job Posting

Intent
Structured job definition.

What student must do

Create form with:

Skill names

Skill weights

Qualification

Min experience

Common Mistakes

Free-text skills without structure

Output

Job stored with criteria

🔹 Task S3-T2: Resume Upload

Intent
Secure file handling.

What student must do

Validate file type

Rename file safely

Store path in DB

Edge Cases

Large files

Corrupt PDFs

Output

Resume stored & linked

🔹 Task S3-T3: Job Application Flow

Intent
Create an application pipeline.

What student must do

Link job + resume

Default status = Applied

Output

Application record created

🟣 SPRINT 4 — RESUME PARSING & SKILL EXTRACTION
🔹 Task S4-T1: Resume Text Extraction

Intent
Convert PDF/DOCX → text.

What student must do

Use parser libs

Handle parse failures

Output

Raw resume text

🔹 Task S4-T2: Text Cleaning

Intent
Improve skill matching accuracy.

Steps

Lowercasing

Remove symbols

Normalize spacing

Output

Cleaned text

🔹 Task S4-T3: Skill Extraction

Intent
Detect relevant skills.

What student must do

Maintain skill dictionary

Match against resume text

Output

List of detected skills

🔴 SPRINT 5 — RULE-BASED WEIGHTED SCORING
🔹 Task S5-T1: Skill Scoring

Intent
Quantify skill relevance.

Logic

Skill present → add weight

Skill missing → no score

Output

Skill score value

🔹 Task S5-T2: Qualification Scoring

Intent
Eligibility filtering.

Logic

Match → bonus

Mismatch → penalty

Output

Qualification score

🔹 Task S5-T3: Experience Scoring

Intent
Fair partial scoring.

Logic

Full if met

Partial if close

Output

Experience score

🔹 Task S5-T4: Final Rule Score

Intent
Unified baseline score.

What student must do

Sum components

Normalize

Output

Base score stored

🟠 SPRINT 6 — AI FEEDBACK & EXPLANATION
🔹 Task S6-T1: Prompt Engineering

Intent
Control AI behavior.

What to include

Resume text

Job criteria

Base score

Instructions to explain, not decide

Output

Stable prompt text

🔹 Task S6-T2: AI Response Parsing

Intent
Prevent unpredictable output.

What student must do

Enforce JSON-like structure

Validate fields

Output

Parsed feedback

🔹 Task S6-T3: Score Adjustment Control

Intent
Prevent AI dominance.

Rule

AI cannot change score by ±10%

Output

Safe final score

🔹 Task S6-T4: Feedback Presentation

Intent
Career guidance.

What student must do

Display strengths & gaps clearly

Output

Feedback page

⚫ SPRINT 7 — RANKING & DASHBOARDS
🔹 Task S7-T1: Ranking Logic

Intent
Prioritize candidates.

Logic

ORDER BY score DESC

Output

Ranked list per job

🔹 Task S7-T2: Recruiter Dashboard

Intent
Decision support.

What student must do

Show rank, score, status

Output

Recruiter shortlist view

🔹 Task S7-T3: Status Management

Intent
Track pipeline.

What student must do

Update status cleanly

Output

Consistent state

⚪ SPRINT 8 — TESTING, DOCS & VIVA
🔹 Task S8-T1: Testing

Intent
Reliability.

What to test

Bad resumes

Missing skills

Invalid users

Output

Bug-free demo

🔹 Task S8-T2: Documentation

Intent
Marks + clarity.

Deliverables

Architecture

Data flow

Algorithms

🔹 Task S8-T3: Viva Prep

Intent
Confidence.

Typical Questions

Why rule-based first?

Why AI bounded?

Bias reduction?
import json
import random

# ==========================================
# CONFIGURATION
# ==========================================
# How many records do you want to generate?
NUM_RECORDS = 140

# Which field do you want to dominate the dataset?
# Options: "Public Sector", "Private Sector", "Entrepreneurship", "Foreign Employment"
TARGET_PREFERENCE = "Public Sector"

# How strong is the bias? (0.8 = 80% of students will choose the target)
BIAS_STRENGTH = 0.7

# ==========================================
# DATA DEFINITIONS
# ==========================================

LIKERT_SCALE = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
SEMESTERS = [
    "First Semester", "Second Semester", "Third Semester", "Fourth Semester",
    "Fifth Semester", "Sixth Semester", "Seventh Semester", "Eighth Semester"
]
PARENTS_OCCUPATION = ["Government Service", "Private Sector", "Business", "Foreign Employment", "Other"]
GENDERS = ["Male", "Female", "Other"]
CAREER_OPTIONS = ["Foreign Employment", "Entrepreneurship", "Private Sector", "Public Sector"]

FACTORS_OPTIONS = [
    "Job Security", "Salary", "Social Prestige", "Family Influence",
    "Personal Interest", "Risk-Taking Ability", "Opportunity Availability", "Education and Skills"
]

# Mapping Questions to their specific Sections/Themes
# C: Public (Q1-4), D: Private (Q5-8), E: Entrepreneurship (Q9-12), F: Foreign (Q13-16)
# G: Education (Q17-20), H: Lifestyle (Q21-24)
QUESTION_MAP = {
    "Public Sector": [1, 2, 3, 4],
    "Private Sector": [5, 6, 7, 8],
    "Entrepreneurship": [9, 10, 11, 12],
    "Foreign Employment": [13, 14, 15, 16]
}

# Questions Q21-Q24 are about Job Security vs Salary. 
# We map specific preferences to these lifestyle choices.
LIFESTYLE_MAP = {
    "Public Sector": ["Job Security", "Stability"], # Prefers Q21, Q22
    "Private Sector": ["Salary", "Growth"],         # Prefers Q23
    "Entrepreneurship": ["Risk", "Balance"],        # Prefers Q24
    "Foreign Employment": ["Salary", "Growth"]      # Prefers Q23
}

def get_weighted_likert(sentiment):
    """Returns a Likert response based on desired sentiment (positive, negative, neutral)."""
    if sentiment == "positive":
        return random.choices(LIKERT_SCALE, weights=[0, 0, 10, 45, 45], k=1)[0]
    elif sentiment == "negative":
        return random.choices(LIKERT_SCALE, weights=[40, 40, 20, 0, 0], k=1)[0]
    else: # mixed/neutral
        return random.choices(LIKERT_SCALE, weights=[10, 20, 40, 20, 10], k=1)[0]

def generate_student_data(index):
    data = {}
    
    # 1. Demographics
    data["Age"] = str(random.randint(19, 26))
    data["Gender"] = random.choice(GENDERS)
    data["Education"] = random.choice(SEMESTERS)
    data["Category_Other"] = random.choice(PARENTS_OCCUPATION) # Maps to Parents' Occupation based on your JSON example

    # 2. Determine Career Preference (Bias Logic)
    if random.random() < BIAS_STRENGTH:
        chosen_interest = TARGET_PREFERENCE
    else:
        # Pick randomly from the remaining options
        remaining = [c for c in CAREER_OPTIONS if c != TARGET_PREFERENCE]
        chosen_interest = random.choice(remaining)
    
    data["Interest_Area"] = chosen_interest

    # 3. Generate Factors based on Interest
    # If Public Sector, likely to pick "Job Security" and "Social Prestige"
    current_factors = []
    if chosen_interest == "Public Sector":
        current_factors = ["Job Security", "Social Prestige", "Opportunity Availability"]
    elif chosen_interest == "Entrepreneurship":
        current_factors = ["Risk-Taking Ability", "Personal Interest", "Salary"]
    elif chosen_interest == "Foreign Employment":
        current_factors = ["Salary", "Opportunity Availability", "Family Influence"]
    elif chosen_interest == "Private Sector":
        current_factors = ["Salary", "Education and Skills", "Personal Interest"]
    
    # Randomly select 2-4 factors from the likely list, plus maybe a random one
    num_factors = random.randint(2, 4)
    # Ensure we don't crash if list is small, sample carefully
    selected_factors = list(set(random.sample(current_factors, min(len(current_factors), 2)) + 
                                random.sample(FACTORS_OPTIONS, 1)))
    data["Factors_Checkboxes"] = selected_factors

    # 4. Generate Survey Answers (Q1 - Q24)
    for q_num in range(1, 25):
        key = f"Survey_Q{q_num}"
        
        # Default sentiment
        sentiment = "neutral"

        # Check which section this question belongs to
        section_category = None
        for cat, q_range in QUESTION_MAP.items():
            if q_num in q_range:
                section_category = cat
                break
        
        # --- Logic for Q1-Q16 (Specific Career Sections) ---
        if section_category:
            if section_category == chosen_interest:
                sentiment = "positive"  # Agrees with their choice
            else:
                sentiment = "negative" # Disagrees/Neutral about others

        # --- Logic for Q17-Q20 (Education - General) ---
        elif 17 <= q_num <= 20:
            # Generally students agree education is good, regardless of career
            sentiment = "positive" 

        # --- Logic for Q21-Q24 (Lifestyle/Security) ---
        elif 21 <= q_num <= 24:
            # Q21: Job Security, Q22: Stability
            if q_num in [21, 22]:
                if chosen_interest == "Public Sector": sentiment = "positive"
                elif chosen_interest == "Entrepreneurship": sentiment = "negative"
                else: sentiment = "neutral"
            
            # Q23: Salary > Security
            if q_num == 23:
                if chosen_interest in ["Foreign Employment", "Private Sector"]: sentiment = "positive"
                elif chosen_interest == "Public Sector": sentiment = "negative"
            
            # Q24: Work Life Balance
            if q_num == 24:
                sentiment = "positive" # Everyone likes work-life balance generally

        data[key] = get_weighted_likert(sentiment)

    return data

# ==========================================
# EXECUTION
# ==========================================

dataset = [generate_student_data(i) for i in range(NUM_RECORDS)]

# Convert to JSON string
json_output = json.dumps(dataset, indent=4)

# Print or Save
print(f"Generated {NUM_RECORDS} records with bias toward {TARGET_PREFERENCE}")
# Write to file
with open("career_survey_data.json", "w") as f:
    f.write(json_output)

# Print a preview of the first record
print(json_output[:1000] + "...")
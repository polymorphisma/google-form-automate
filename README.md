# Google Form Automate

CLI tool for public Google Forms:

1. Discover Google's hidden `entry.xxxxx` field IDs from a `viewform` URL.
2. Generate JSON response data.
3. Optionally submit that data to the form.

The tool does **not** submit anything unless you pass `--submit`.

## Requirements

- Python 3.14 or newer
- `requests`

This machine has the Python launcher available as `py`.

Install dependencies if needed:

```powershell
py -m pip install requests faker
```

## Current Form

The current discovered mapping is saved in:

```text
discovered_employee_mapping.json
```

That mapping was generated from this form:

```text
https://docs.google.com/forms/d/e/1FAIpQLSc-E7x_Nl0jJsGLWqGhSmhff9XKIbwpinONCs8EHK47rYoevg/viewform?usp=dialog
```

## Full Runbook

### 1. Discover the form mapping

Run this once for a new form, or when the form questions/options change:

```powershell
py automate_cli.py discover --form-url "https://docs.google.com/forms/d/e/1FAIpQLSc-E7x_Nl0jJsGLWqGhSmhff9XKIbwpinONCs8EHK47rYoevg/viewform?usp=dialog" --mapping discovered_employee_mapping.json
```

This prints all usable field keys. Use those keys with `--set`.

### 2. Generate data only, no submission

This creates `employee_data.json` and does not contact Google for submission:

```powershell
py automate_cli.py fill --mapping discovered_employee_mapping.json --records 100 --choose "Gender=Male,Female" --set "Age=20-30" --set "Marital_Status=Unmarried" --set "Education_Level=Bachelor's" --set "Position_in_Company=Junior" --set "Work_Experience=1-3 years" --set "Monthly_Income=NPR 30,001- NPR 50,000" --scale-bias-range 0.6,0.8 --scale-bias-values 3,4 --scale-category-size 6 --output employee_data.json
```

### 3. Inspect generated data

Open `employee_data.json` and check a few rows before submission.

Important behavior:

- `--set KEY=VALUE` locks a field to a fixed value for all generated records.
- `--choose KEY=A,B` randomly chooses from only those listed options, for example `--choose "Gender=Male,Female"`.
- Unset multiple-choice fields are picked randomly from the form's options.
- The `Name` field gets generated first/last names using Faker.
- `1-5` scale questions are biased using the scale options below.

### 4. Scale bias options

Use one fixed bias for all `1-5` scale questions:

```powershell
--scale-bias 0.7 --scale-bias-values 3,4
```

This means answers `3` or `4` are chosen about 70% of the time.

Use a different random bias per category:

```powershell
--scale-bias-range 0.6,0.8 --scale-bias-values 3,4 --scale-category-size 6
```

This treats every 6 consecutive `1-5` questions as one category. Each category gets its own random bias between 60% and 80% toward `3` and `4`. The remaining probability is randomly split across the other scale values.

### 5. Submit responses

Only add `--submit` after inspecting the generated JSON:

```powershell
py automate_cli.py fill --mapping discovered_employee_mapping.json --records 100 --choose "Gender=Male,Female" --set "Age=20-30" --set "Marital_Status=Unmarried" --set "Education_Level=Bachelor's" --set "Position_in_Company=Junior" --set "Work_Experience=1-3 years" --set "Monthly_Income=NPR 30,001- NPR 50,000" --scale-bias-range 0.6,0.8 --scale-bias-values 3,4 --scale-category-size 6 --output employee_data.json --submit
```

The form URL is stored in the mapping, so you usually do not need to pass `--form-url` during fill/submit.

### 6. Useful checks

Show commands:

```powershell
py automate_cli.py --help
py automate_cli.py discover --help
py automate_cli.py fill --help
```

Check syntax:

```powershell
py -m py_compile automate_cli.py form_discovery.py form_submitter.py generic_dataset.py
```

## Main Files

- `automate_cli.py` - command-line interface
- `form_discovery.py` - reads a public Google Form and creates mapping JSON
- `generic_dataset.py` - generates response rows and weighted 1-5 answers
- `form_submitter.py` - submits generated rows to Google Forms
- `discovered_employee_mapping.json` - mapping for the current employee survey form


## Recommended 320-response command

Generate 320 realistic records without submitting:

```powershell
py automate_cli.py fill --mapping discovered_employee_mapping.json --records 320 --choose "Gender=Male,Female" --smart-demographics --scale-bias 0.75 --scale-bias-values 3,4 --output employee_data.json
```

This applies these consistency rules:

- Bachelor's: age 20-30, junior/below 1 year/below NPR 30,000 or mid level/1-3 years/NPR 30,001-50,000.
- Master's: age 20-30, mid or senior/1-3 years/NPR 50,001-80,000 or managerial/4-6 years/above NPR 80,000.
- MPhil or PhD: age 31-40, managerial, 4-6 years or above 6 years, above NPR 80,000.
- Gender: random Male/Female only.
- Ratings: 3 or 4 around 75%; 1, 2, and 5 share the remaining 25%.

Submit after checking `employee_data.json`:

```powershell
py automate_cli.py fill --mapping discovered_employee_mapping.json --records 320 --choose "Gender=Male,Female" --smart-demographics --scale-bias 0.75 --scale-bias-values 3,4 --output employee_data.json --submit
```


## Use Names From CSV

Use the salary reference CSV names when generating responses:

```powershell
py automate_cli.py fill --mapping discovered_employee_mapping.json --records 320 --names-csv "C:\Users\shrawan.sunar\Downloads\salary  Refrence (1).xls - Sheet1.csv" --choose "Gender=Male,Female" --smart-demographics --scale-bias 0.75 --scale-bias-values 3,4 --output employee_data.json
```

The CSV must include an `Emp Name` or `Name` column. Names are used in CSV order; Faker is only used if you request more records than there are CSV names.

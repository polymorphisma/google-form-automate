import csv
import json
import random

from faker import Faker


FAKER = Faker()
LIKERT_OPTIONS = ["1", "2", "3", "4", "5"]
SMART_DEMOGRAPHIC_KEYS = {
    "Education_Level",
    "Age",
    "Position_in_Company",
    "Work_Experience",
    "Monthly_Income",
}


def load_mapping(path):
    with open(path, "r") as f:
        return json.load(f)


def parse_set_values(values):
    parsed = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Expected KEY=VALUE, got: {value}")
        key, raw = value.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if not key or not raw:
            raise ValueError(f"Expected KEY=VALUE, got: {value}")
        parsed[key] = raw
    return parsed


def parse_choose_values(values):
    parsed = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Expected KEY=A,B, got: {value}")
        key, raw = value.split("=", 1)
        key = key.strip()
        choices = [item.strip() for item in raw.split(",") if item.strip()]
        if not key or not choices:
            raise ValueError(f"Expected KEY=A,B, got: {value}")
        parsed[key] = choices
    return parsed


def parse_bias_values(value):
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    if not parsed:
        raise ValueError("scale bias values cannot be empty")
    unknown = sorted(set(parsed) - set(LIKERT_OPTIONS))
    if unknown:
        raise ValueError(f"Scale bias values must be 1, 2, 3, 4, or 5. Invalid: {', '.join(unknown)}")
    return parsed


def parse_bias_range(value):
    if not value:
        return None
    pieces = [item.strip() for item in value.split(",") if item.strip()]
    if len(pieces) != 2:
        raise ValueError("scale bias range must look like MIN,MAX, for example 0.6,0.8")

    minimum = float(pieces[0])
    maximum = float(pieces[1])
    if not 0 <= minimum <= maximum <= 1:
        raise ValueError("scale bias range values must satisfy 0 <= MIN <= MAX <= 1")
    return minimum, maximum


def normalize_choice(value):
    return (
        str(value)
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace(" ", "")
        .strip()
        .lower()
    )


def canonical_option(value, options):
    if not options:
        return value
    if value in options:
        return value

    normalized = normalize_choice(value)
    for option in options:
        if normalize_choice(option) == normalized:
            return option

    allowed = ", ".join(options)
    raise ValueError(f"Invalid option: {value}. Allowed values: {allowed}")


def canonical_choices(values, options):
    canonical = []
    for value in values:
        option = canonical_option(value, options)
        if option not in canonical:
            canonical.append(option)
    return canonical


def load_names_csv(path):
    if not path:
        return []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"No header row found in names CSV: {path}")

        name_column = None
        for fieldname in reader.fieldnames:
            if fieldname and fieldname.strip().lower() in {"emp name", "name"}:
                name_column = fieldname
                break
        if name_column is None:
            available = ", ".join(fieldname for fieldname in reader.fieldnames if fieldname)
            raise ValueError(f"Could not find an Emp Name or Name column in {path}. Available columns: {available}")

        names = []
        for row in reader:
            name = (row.get(name_column) or "").strip()
            if name:
                names.append(name)

    if not names:
        raise ValueError(f"No names found in {path}")
    return names


def random_name(index, names=None):
    if names and index < len(names):
        return names[index]
    return f"{FAKER.first_name()} {FAKER.last_name()}"


def is_likert_scale(options):
    return [str(option) for option in options] == LIKERT_OPTIONS


def weighted_likert_choice(options, scale_bias, scale_bias_values):
    if not 0 <= scale_bias <= 1:
        raise ValueError("scale_bias must be between 0 and 1")

    biased_values = [canonical_option(value, options) for value in scale_bias_values]
    other_values = [option for option in options if option not in biased_values]

    if not other_values or random.random() < scale_bias:
        return random.choice(biased_values)
    return random.choice(other_values)


def build_scale_biases(field_keys, options_by_key, scale_bias, scale_bias_range, scale_category_size):
    if scale_category_size < 1:
        raise ValueError("scale_category_size must be at least 1")

    if scale_bias_range is None:
        if not 0 <= scale_bias <= 1:
            raise ValueError("scale_bias must be between 0 and 1")
        return {key: scale_bias for key in field_keys if is_likert_scale(options_by_key.get(key, []))}

    likert_keys = [key for key in field_keys if is_likert_scale(options_by_key.get(key, []))]
    biases = {}
    for start in range(0, len(likert_keys), scale_category_size):
        category_keys = likert_keys[start:start + scale_category_size]
        category_bias = random.uniform(scale_bias_range[0], scale_bias_range[1])
        for key in category_keys:
            biases[key] = category_bias
    return biases


def value_for_field(key, options, fixed_values, choice_values, index, scale_bias, scale_bias_values, names=None):
    if key in fixed_values:
        return canonical_option(fixed_values[key], options)

    if key in choice_values:
        return random.choice(choice_values[key])

    normalized = key.lower()
    if normalized == "name" or normalized.endswith("_name"):
        return random_name(index, names=names)

    if is_likert_scale(options):
        return weighted_likert_choice(options, scale_bias, scale_bias_values)

    if options:
        return random.choice(options)

    return f"Sample {index + 1}"


def validate_field_overrides(mapping, fixed_values, choice_values):
    fields = mapping.get("fields", {})
    options_by_key = mapping.get("field_options", {})

    unknown = sorted((set(fixed_values) | set(choice_values)) - set(fields))
    if unknown:
        known = ", ".join(fields)
        raise ValueError(f"Unknown field(s): {', '.join(unknown)}. Known fields: {known}")

    overlap = sorted(set(fixed_values) & set(choice_values))
    if overlap:
        raise ValueError(f"Cannot use both --set and --choose for: {', '.join(overlap)}")

    for key, value in fixed_values.items():
        canonical_option(value, options_by_key.get(key, []))

    canonical_choice_values = {}
    for key, values in choice_values.items():
        canonical_choice_values[key] = canonical_choices(values, options_by_key.get(key, []))
    return canonical_choice_values


def profile_value(options_by_key, key, value):
    return canonical_option(value, options_by_key.get(key, []))


def choose_profile(options_by_key, key, values):
    return random.choice([profile_value(options_by_key, key, value) for value in values])


def set_profile_field(row, key, value, options_by_key, locked_keys):
    if key in row and key not in locked_keys:
        row[key] = profile_value(options_by_key, key, value)


def apply_smart_demographics(row, options_by_key, fixed_values, choice_values):
    locked_keys = set(fixed_values) | set(choice_values)

    if "Education_Level" not in locked_keys:
        row["Education_Level"] = choose_profile(
            options_by_key,
            "Education_Level",
            ["Bachelor's", "Master's", "MPhil", "PhD"],
        )

    education = row.get("Education_Level")

    if education == "Bachelor's":
        set_profile_field(row, "Age", "20-30", options_by_key, locked_keys)
        if random.random() < 0.55:
            set_profile_field(row, "Position_in_Company", "Junior", options_by_key, locked_keys)
            set_profile_field(row, "Work_Experience", "Below 1 year", options_by_key, locked_keys)
            set_profile_field(row, "Monthly_Income", "Below NPR 30,000", options_by_key, locked_keys)
        else:
            set_profile_field(row, "Position_in_Company", "Mid Level", options_by_key, locked_keys)
            set_profile_field(row, "Work_Experience", "1-3 years", options_by_key, locked_keys)
            set_profile_field(row, "Monthly_Income", "NPR 30,001- NPR 50,000", options_by_key, locked_keys)
        return

    if education == "Master's":
        set_profile_field(row, "Age", "20-30", options_by_key, locked_keys)
        if random.random() < 0.7:
            set_profile_field(
                row,
                "Position_in_Company",
                choose_profile(options_by_key, "Position_in_Company", ["Mid Level", "Senior"]),
                options_by_key,
                locked_keys,
            )
            set_profile_field(row, "Work_Experience", "1-3 years", options_by_key, locked_keys)
            set_profile_field(row, "Monthly_Income", "NPR 50,001- NPR 80,000", options_by_key, locked_keys)
        else:
            set_profile_field(row, "Position_in_Company", "Managerial", options_by_key, locked_keys)
            set_profile_field(row, "Work_Experience", "4-6 years", options_by_key, locked_keys)
            set_profile_field(row, "Monthly_Income", "Above NPR 80,000", options_by_key, locked_keys)
        return

    if education in {"MPhil", "PhD"}:
        set_profile_field(row, "Age", "31-40", options_by_key, locked_keys)
        set_profile_field(row, "Position_in_Company", "Managerial", options_by_key, locked_keys)
        set_profile_field(row, "Work_Experience", choose_profile(options_by_key, "Work_Experience", ["4-6 years", "Above 6 years"]), options_by_key, locked_keys)
        set_profile_field(row, "Monthly_Income", "Above NPR 80,000", options_by_key, locked_keys)
        return

    if education == "+2":
        set_profile_field(row, "Age", "20-30", options_by_key, locked_keys)
        set_profile_field(row, "Position_in_Company", "Junior", options_by_key, locked_keys)
        set_profile_field(row, "Work_Experience", "Below 1 year", options_by_key, locked_keys)
        set_profile_field(row, "Monthly_Income", "Below NPR 30,000", options_by_key, locked_keys)


def generate_generic_dataset(
    mapping_path,
    records=1,
    fixed_values=None,
    choice_values=None,
    seed=None,
    scale_bias=0.7,
    scale_bias_values=None,
    scale_bias_range=None,
    scale_category_size=6,
    smart_demographics=False,
    names_csv=None,
):
    if records < 1:
        raise ValueError("records must be at least 1")
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    scale_bias_values = scale_bias_values or ["3", "4"]

    mapping = load_mapping(mapping_path)
    names = load_names_csv(names_csv)
    fixed_values = fixed_values or {}
    choice_values = choice_values or {}
    choice_values = validate_field_overrides(mapping, fixed_values, choice_values)

    field_keys = list(mapping.get("fields", {}))
    options_by_key = mapping.get("field_options", {})
    scale_biases = build_scale_biases(
        field_keys,
        options_by_key,
        scale_bias,
        scale_bias_range,
        scale_category_size,
    )

    dataset = []
    for index in range(records):
        row = {}
        for key in field_keys:
            row[key] = value_for_field(
                key,
                options_by_key.get(key, []),
                fixed_values,
                choice_values,
                index,
                scale_biases.get(key, scale_bias),
                scale_bias_values,
                names=names,
            )
        if smart_demographics:
            apply_smart_demographics(row, options_by_key, fixed_values, choice_values)
        dataset.append(row)
    return dataset


def write_dataset(path, rows):
    with open(path, "w") as f:
        json.dump(rows, f, indent=4)








import json
import random


DEFAULT_NAMES = [
    "Aarav Sharma",
    "Anita Thapa",
    "Bikash Gurung",
    "Kiran Shrestha",
    "Nisha Rai",
    "Prakash Adhikari",
    "Suman Karki",
    "Mina Tamang",
]
LIKERT_OPTIONS = ["1", "2", "3", "4", "5"]


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


def random_name(index):
    if index < len(DEFAULT_NAMES):
        return DEFAULT_NAMES[index]
    return f"Respondent {index + 1}"


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


def value_for_field(key, options, fixed_values, choice_values, index, scale_bias, scale_bias_values):
    if key in fixed_values:
        return canonical_option(fixed_values[key], options)

    if key in choice_values:
        return random.choice(choice_values[key])

    normalized = key.lower()
    if normalized == "name" or normalized.endswith("_name"):
        return random_name(index)

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
):
    if records < 1:
        raise ValueError("records must be at least 1")
    if seed is not None:
        random.seed(seed)

    scale_bias_values = scale_bias_values or ["3", "4"]

    mapping = load_mapping(mapping_path)
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
            )
        dataset.append(row)
    return dataset


def write_dataset(path, rows):
    with open(path, "w") as f:
        json.dump(rows, f, indent=4)

import argparse
import json

from form_discovery import discover_form, write_mapping
from form_submitter import submit_dataset
from generic_dataset import generate_generic_dataset, parse_bias_range, parse_bias_values, parse_choose_values, parse_set_values, write_dataset


DEFAULT_MAPPING = "form_mapping.json"
DEFAULT_OUTPUT = "form_data.json"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gform-automate",
        description="Discover Google Form fields, generate response data, and optionally submit it.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser("discover", help="Create mapping JSON from a public Google Form URL.")
    discover.add_argument("--form-url", required=True, help="Google Forms viewform URL.")
    discover.add_argument(
        "--mapping",
        default=DEFAULT_MAPPING,
        help=f"Where to write mapping JSON. Default: {DEFAULT_MAPPING}.",
    )

    fill = subparsers.add_parser("fill", help="Generate responses from a mapping JSON.")
    fill.add_argument(
        "--mapping",
        default=DEFAULT_MAPPING,
        help=f"Mapping JSON from the discover command. Default: {DEFAULT_MAPPING}.",
    )
    fill.add_argument(
        "--records",
        type=int,
        default=1,
        help="Number of responses to generate. Default: 1.",
    )
    fill.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Force a field value. Can be repeated, for example --set Gender=Male.",
    )
    fill.add_argument(
        "--choose",
        action="append",
        default=[],
        metavar="KEY=A,B",
        help="Randomly choose from a restricted option list. Can be repeated, for example --choose Gender=Male,Female.",
    )
    fill.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Where to write generated JSON. Default: {DEFAULT_OUTPUT}.",
    )
    fill.add_argument("--seed", type=int, help="Optional random seed for repeatable generated data.")
    fill.add_argument(
        "--scale-bias",
        type=float,
        default=0.7,
        help="Probability that 1-5 scale questions choose the biased values. Default: 0.7.",
    )
    fill.add_argument(
        "--scale-bias-values",
        default="3,4",
        help="Comma-separated 1-5 values to prefer for scale questions. Default: 3,4.",
    )
    fill.add_argument(
        "--scale-bias-range",
        help="Randomize the scale bias per category using MIN,MAX, for example 0.6,0.8.",
    )
    fill.add_argument(
        "--scale-category-size",
        type=int,
        default=6,
        help="Number of consecutive 1-5 questions in each category when --scale-bias-range is used. Default: 6.",
    )
    fill.add_argument(
        "--smart-demographics",
        action="store_true",
        help="Match education with realistic age, position, experience, and income combinations.",
    )
    fill.add_argument(
        "--submit",
        action="store_true",
        help="Submit generated responses after writing the JSON file.",
    )
    fill.add_argument(
        "--form-url",
        help="Optional form URL override. Usually not needed because it is stored in the mapping.",
    )
    fill.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between submissions when --submit is used. Default: 1.0.",
    )
    return parser


def run_discover(args):
    mapping = discover_form(args.form_url)
    write_mapping(args.mapping, mapping)

    print(f"Discovered {len(mapping['fields'])} fields and wrote {args.mapping}.")
    print("Fields:")
    for key, label in mapping.get("field_labels", {}).items():
        options = mapping.get("field_options", {}).get(key, [])
        suffix = f" ({', '.join(options)})" if options else ""
        print(f"- {key}: {label}{suffix}")
    return 0


def run_fill(args):
    fixed_values = parse_set_values(args.set)
    choice_values = parse_choose_values(args.choose)
    rows = generate_generic_dataset(
        mapping_path=args.mapping,
        records=args.records,
        fixed_values=fixed_values,
        choice_values=choice_values,
        seed=args.seed,
        scale_bias=args.scale_bias,
        scale_bias_values=parse_bias_values(args.scale_bias_values),
        scale_bias_range=parse_bias_range(args.scale_bias_range),
        scale_category_size=args.scale_category_size,
        smart_demographics=args.smart_demographics,
    )
    write_dataset(args.output, rows)

    print(f"Generated {len(rows)} records at {args.output}.")
    if rows:
        print("Preview:")
        print(json.dumps(rows[0], indent=2))

    if not args.submit:
        print("Dry run only. Add --submit to post these records to the form.")
        return 0

    successes, total = submit_dataset(
        mapping_path=args.mapping,
        data_path=args.output,
        form_url=args.form_url,
        delay=args.delay,
    )
    print(f"Finished: {successes}/{total} submissions succeeded.")
    return 0 if successes == total else 1


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "discover":
        return run_discover(args)
    if args.command == "fill":
        return run_fill(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())



import json
import re
from urllib.parse import urlsplit, urlunsplit

import requests


DEFAULT_STATIC_DATA = {
    "fvv": "1",
    "draftResponse": "[]",
    "pageHistory": "0",
}


def to_form_response_url(form_url):
    parts = urlsplit(form_url.strip())
    path = parts.path.replace("/viewform", "/formResponse")
    if not path.endswith("/formResponse"):
        path = path.rstrip("/") + "/formResponse"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def fetch_form_html(form_url):
    response = requests.get(
        form_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def extract_public_load_data(html):
    match = re.search(r"var FB_PUBLIC_LOAD_DATA_ = (.*?);</script>", html, re.DOTALL)
    if not match:
        match = re.search(r"var FB_PUBLIC_LOAD_DATA_ = (.*?);", html, re.DOTALL)
    if not match:
        raise ValueError("Could not find FB_PUBLIC_LOAD_DATA_ in the form HTML")
    return json.loads(match.group(1))


def normalize_label(label):
    label = re.sub(r"\s+", " ", str(label)).strip()
    return label.rstrip(" *")


def field_key(label):
    key = normalize_label(label)
    key = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_")
    return key or "Field"


def unique_key(base, seen):
    key = base
    counter = 2
    while key in seen:
        key = f"{base}_{counter}"
        counter += 1
    seen.add(key)
    return key


def extract_options(entry):
    options = []
    if len(entry) > 1 and isinstance(entry[1], list):
        for option in entry[1]:
            if isinstance(option, list) and option and isinstance(option[0], str):
                options.append(option[0])
            elif isinstance(option, str):
                options.append(option)
    return options


def extract_fields(public_load_data):
    fields = []
    seen = set()

    def visit(node):
        if not isinstance(node, list):
            return

        if len(node) >= 5 and isinstance(node[1], str) and isinstance(node[4], list):
            label = normalize_label(node[1])
            entries = []
            for entry in node[4]:
                if isinstance(entry, list) and entry and isinstance(entry[0], int):
                    entries.append({
                        "entry_id": f"entry.{entry[0]}",
                        "options": extract_options(entry),
                    })

            if label and entries:
                key = unique_key(field_key(label), seen)
                fields.append({
                    "key": key,
                    "label": label,
                    "entry_id": entries[0]["entry_id"],
                    "options": entries[0]["options"],
                })
                return

        for child in node:
            visit(child)

    visit(public_load_data)
    return fields


def extract_fbzx(html):
    match = re.search(r'name="fbzx" value="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'"fbzx"\s*,\s*"?(-?\d+)"?', html)
    if match:
        return match.group(1)
    return None


def discover_form(form_url):
    html = fetch_form_html(form_url)
    data = extract_public_load_data(html)
    fields = extract_fields(data)
    if not fields:
        raise ValueError("No fields were discovered from the form")

    static_data = dict(DEFAULT_STATIC_DATA)
    fbzx = extract_fbzx(html)
    if fbzx:
        static_data["fbzx"] = fbzx

    return {
        "form_url": to_form_response_url(form_url),
        "fields": {field["key"]: field["entry_id"] for field in fields},
        "field_labels": {field["key"]: field["label"] for field in fields},
        "field_options": {field["key"]: field["options"] for field in fields if field["options"]},
        "static_data": static_data,
    }


def write_mapping(path, mapping):
    with open(path, "w") as f:
        json.dump(mapping, f, indent=4)

import json
import time

import requests


def to_form_response_url(form_url):
    if not form_url:
        return form_url

    base = form_url.strip().split("?", 1)[0]
    if base.endswith("/viewform"):
        return base[:-len("/viewform")] + "/formResponse"
    if base.endswith("/formResponse"):
        return base
    return base.rstrip("/") + "/formResponse"


class GoogleFormSubmitter:
    def __init__(self, mapping_path, form_url=None, error_path="error_response.html"):
        with open(mapping_path, "r") as f:
            self.mapping = json.load(f)

        self.url = to_form_response_url(form_url or self.mapping["form_url"])
        self.field_map = self.mapping["fields"]
        self.static_data = self.mapping.get("static_data", {})
        self.error_path = error_path
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://docs.google.com",
            "Referer": self.url,
        }

    def prepare_payload(self, row):
        payload = {}
        for field_key, value in row.items():
            entry_id = self.field_map.get(field_key)
            if entry_id is None:
                print(f"Warning: Key '{field_key}' not found in mapping.")
                continue
            payload[entry_id] = value

        payload.update(self.static_data)
        return payload

    def submit(self, row):
        response = requests.post(
            self.url,
            data=self.prepare_payload(row),
            headers=self.headers,
            timeout=30,
        )

        if response.status_code == 200:
            return True

        with open(self.error_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"[ERROR] Failed with status {response.status_code}; wrote {self.error_path}")
        return False


def submit_dataset(mapping_path, data_path, form_url=None, delay=1.0, error_path="error_response.html"):
    submitter = GoogleFormSubmitter(mapping_path, form_url=form_url, error_path=error_path)

    with open(data_path, "r") as f:
        rows = json.load(f)

    print(f"Starting submission for {len(rows)} records...")
    successes = 0
    for index, row in enumerate(rows, start=1):
        try:
            if submitter.submit(row):
                successes += 1
                print(f"[SUCCESS] Submitted record {index}/{len(rows)}")
        except Exception as exc:
            print(f"[EXCEPTION] Record {index}/{len(rows)} failed: {exc}")
        time.sleep(delay)

    return successes, len(rows)

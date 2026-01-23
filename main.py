import requests
import json
import time

class GoogleFormSubmitter:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.url = self.config['form_url']
        self.field_map = self.config['fields']
        self.static_data = self.config['static_data']
        
        # Headers mimicking a real browser (Brave/Linux)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://docs.google.com',
            'Referer': self.url
        }

    def prepare_payload(self, user_data):
        """
        Converts readable user data into Google Form 'entry.XXXX' payload.
        """
        payload = {}
        
        # Add dynamic fields from user input
        for readable_key, value in user_data.items():
            if readable_key in self.field_map:
                entry_id = self.field_map[readable_key]
                payload[entry_id] = value
            else:
                print(f"Warning: Key '{readable_key}' not found in mapping.")
        
        # Add required static fields (metadata)
        payload.update(self.static_data)
        return payload

    def submit(self, user_data):
        payload = self.prepare_payload(user_data)
        
        try:
            # Send POST request
            response = requests.post(self.url, data=payload, headers=self.headers)
            
            if response.status_code == 200:
                print(f"[SUCCESS] Submitted data for Age: {user_data.get('Age', 'Unknown')}")
            else:
                print(f"[ERROR] Failed with status {response.status_code}")

                # print(response.text) # Uncomment to debug HTML response
                with open('error_response.html', 'w') as f:
                    f.write(response.text)
        except Exception as e:
            print(f"[EXCEPTION] {str(e)}")

def main():
    # Initialize
    submitter = GoogleFormSubmitter('mapping.json')
    
    # Load Data
    with open('career_survey_data.json', 'r') as f:
        data_list = json.load(f)
    
    # Execute Loop
    print(f"Starting automation for {len(data_list)} entries...")
    for entry in data_list:
        submitter.submit(entry)
        time.sleep(1) # Polite delay to avoid rate limiting

if __name__ == "__main__":
    main()

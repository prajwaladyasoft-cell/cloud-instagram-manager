import os
import time
import requests
from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

app = Flask(__name__)

# ---------------------------------------------------------
# DATABASE CONFIGURATION (SUPABASE REST API)
# ---------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
TABLE_URL = f"{SUPABASE_URL}/rest/v1/instagram_accounts"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"  # Tells Supabase to overwrite if profile exists
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/share', methods=['POST'])
def handle_share():
    # 1. Capture the inputs from our index.html form
    profile_name = request.form.get('profile_name')
    username = request.form.get('username')
    password = request.form.get('password')
    image_url = request.form.get('image_url')
    description = request.form.get('description')

    # 2. Database Sync: If user input a password, update Supabase
    if username and password:
        account_data = {
            "profile_name": profile_name,
            "username": username,
            "password": password
        }
        try:
            # Send a POST request to upsert rows into Supabase
            requests.post(TABLE_URL, json=account_data, headers=HEADERS)
            print(f"Credentials updated online for {profile_name}")
        except Exception as e:
            print(f"Database update failed: {e}")
    else:
        # If fields are left blank, pull the existing saved credentials from Supabase
        try:
            response = requests.get(f"{TABLE_URL}?profile_name=eq.{profile_name}", headers=HEADERS)
            if response.status_code == 200 and len(response.json()) > 0:
                saved_account = response.json()[0]
                username = saved_account['username']
                password = saved_account['password']
                print(f"Retrieved saved credentials for {profile_name}")
        except Exception as e:
            print(f"Failed to fetch credentials from Supabase: {e}")

    # 3. Configure Selenium Webdriver for Cloud Environment
    options = Options()
    options.add_argument("--headless=new")  # STRICTLY REQUIRED ON CLOUD SERVERS
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Direct paths to the custom cloud binary installations from render.yaml
    options.binary_location = "/opt/render/project/.render/chrome/chrome-linux64/chrome"
    chrome_service = Service("/opt/render/project/.render/chrome/chromedriver-linux64/chromedriver")

    try:
        # Initialize browser with service paths
        driver = webdriver.Chrome(service=chrome_service, options=options)
        
        # Hide Selenium signature
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 4. Open Instagram Login Page
        print(f"Launching automation for {profile_name}...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(8)  # Let the page fully render
        
        # Find login inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if len(inputs) >= 2:
            username_input = inputs[0]
            password_input = inputs[1]
            
            # Type credentials carefully mimicking human interaction
            for char in username:
                username_input.send_keys(char)
                time.sleep(0.05)
                
            for char in password:
                password_input.send_keys(char)
                time.sleep(0.05)
                
            password_input.send_keys(Keys.ENTER)
            print("Login submitted. Waiting for dashboard...")
            time.sleep(15)  # Pause window for authentication processing
        
        # 5. Load the Home Page to confirm session placement
        driver.get("https://www.instagram.com/")
        time.sleep(6)
        
        # Close browser session safely
        driver.quit()
        print("Automation processing batch sequence finished successfully.")
        
    except Exception as error:
        print(f"Automation Execution Failure: {error}")
        return f"Automation Halted: {error}", 500

    # Redirect back to home with success status for browser notification banner
    return redirect(url_for('index', status='success', account=profile_name))

if __name__ == '__main__':
    app.run(debug=True)

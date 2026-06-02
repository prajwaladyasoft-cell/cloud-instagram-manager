import os
import time
import threading
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
    "Prefer": "resolution=merge-duplicates"
}

def run_instagram_automation(profile_name, username, password):
    """Runs the heavy Selenium task in a separate background thread to prevent Render timeouts."""
    options = Options()
    options.add_argument("--headless=new")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    base_dir = os.getcwd()
    chrome_path = os.path.join(base_dir, ".render", "chrome", "chrome-linux64", "chrome")
    driver_path = os.path.join(base_dir, ".render", "chrome", "chromedriver-linux64", "chromedriver")

    options.binary_location = chrome_path
    chrome_service = Service(driver_path)

    try:
        print(f"Starting background automation session for {profile_name}...")
        driver = webdriver.Chrome(service=chrome_service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(8)
        
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if len(inputs) >= 2:
            username_input = inputs[0]
            password_input = inputs[1]
            
            for char in username:
                username_input.send_keys(char)
                time.sleep(0.05)
                
            for char in password:
                password_input.send_keys(char)
                time.sleep(0.05)
                
            password_input.send_keys(Keys.ENTER)
            print("Login form submitted successfully inside background execution pipeline.")
            time.sleep(15)
        
        driver.get("https://www.instagram.com/")
        time.sleep(6)
        driver.quit()
        print(f"Background automation completed cleanly for {profile_name}.")
        
    except Exception as error:
        print(f"Automation Background Thread Failure: {error}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/share', methods=['POST'])
def handle_share():
    profile_name = request.form.get('profile_name')
    username = request.form.get('username')
    password = request.form.get('password')

    # Database Sync Strategy
    if username and password:
        account_data = {
            "profile_name": profile_name,
            "username": username,
            "password": password
        }
        try:
            requests.post(TABLE_URL, json=account_data, headers=HEADERS)
            print(f"Database row upserted cleanly for {profile_name}")
        except Exception as e:
            print(f"Database update failed: {e}")
    else:
        try:
            response = requests.get(f"{TABLE_URL}?profile_name=eq.{profile_name}", headers=HEADERS)
            if response.status_code == 200 and len(response.json()) > 0:
                saved_account = response.json()[0]
                username = saved_account['username']
                password = saved_account['password']
                print(f"Retrieved credentials out of storage for {profile_name}")
        except Exception as e:
            print(f"Database fetch layout failed: {e}")

    # Fire and forget the heavy automation job to a background process worker thread
    if username and password:
        threading.Thread(target=run_instagram_automation, args=(profile_name, username, password)).start()
        print("Automation kicked off to sub-process thread wrapper.")
    else:
        print("Missing credentials context block. Skipping execution routine steps.")

    # Instantly returns response back to browser so Render remains happy and never drops the line
    return redirect(url_for('index', status='success', account=profile_name))

if __name__ == '__main__':
    app.run(debug=True)

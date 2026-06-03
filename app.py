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
    "Prefer": "resolution=merge-duplicates"
}

@app.route('/')
def index():
    status = request.args.get('status')
    msg = request.args.get('msg', '')
    account = request.args.get('account', '')
    return render_template('index.html', status=status, msg=msg, account=account)

@app.route('/share', methods=['POST'])
def handle_share():
    profile_name = request.form.get('profile_name')
    username = request.form.get('username')
    password = request.form.get('password')

    print(f"\n[ONLINE EXECUTION] Processing live session for: {profile_name}")

    # 1. Sync data immediately with your Supabase Table
    if username and password:
        account_data = {"profile_name": profile_name, "username": username, "password": password}
        try:
            requests.post(TABLE_URL, json=account_data, headers=HEADERS)
        except Exception as e:
            print(f"Database save error: {e}")
    else:
        try:
            response = requests.get(f"{TABLE_URL}?profile_name=eq.{profile_name}", headers=HEADERS)
            if response.status_code == 200 and len(response.json()) > 0:
                username = response.json()[0]['username']
                password = response.json()[0]['password']
        except Exception as e:
            return redirect(url_for('index', status='error', msg=f"Supabase Read Error: {e}"))

    if not username or not password:
        return redirect(url_for('index', status='error', msg="No saved account credentials found."))

    # 2. Configure Cloud Driver
    options = Options()
    options.add_argument("--headless=new")  # Strictly mandatory on cloud containers
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1024")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

    base_dir = os.getcwd()
    chrome_path = os.path.join(base_dir, ".render", "chrome", "chrome-linux64", "chrome")
    driver_path = os.path.join(base_dir, ".render", "chrome", "chromedriver-linux64", "chromedriver")

    options.binary_location = chrome_path
    chrome_service = Service(driver_path)

    try:
        print("[STEP 1] Starting Browser Engine...")
        driver = webdriver.Chrome(service=chrome_service, options=options)
        
        print("[STEP 2] Navigating to Instagram Auth Server...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(7)
        
        print("[STEP 3] Locating form elements...")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if len(inputs) >= 2:
            print("[STEP 4] Executing remote input injection fields...")
            inputs[0].send_keys(username)
            time.sleep(0.5)
            inputs[1].send_keys(password)
            time.sleep(0.5)
            
            print("[STEP 5] Clicking submit trigger button...")
            inputs[1].send_keys(Keys.ENTER)
            time.sleep(12) # Give the server ample time to log in
            
            final_url = driver.current_url
            print(f"[COMPLETE] Ended tracking route sequence at: {final_url}")
            driver.quit()
            
            # If successfully forwarded or redirected away from login page
            if "login" not in final_url.lower():
                return redirect(url_for('index', status='success', account=profile_name, msg=f"Successfully Authenticated! Connected to profile route: {final_url}"))
            else:
                return redirect(url_for('index', status='error', msg="Authentication failed. Check your Instagram credentials."))
        else:
            driver.quit()
            return redirect(url_for('index', status='error', msg="Failed to extract elements. Instagram might be blocking cloud request traffic patterns."))

    except Exception as error:
        print(f"[CRITICAL FAILURE] Stopped processing layout: {error}")
        return redirect(url_for('index', status='error', msg=f"Server Exception: {error}"))

if __name__ == '__main__':
    app.run(debug=True)

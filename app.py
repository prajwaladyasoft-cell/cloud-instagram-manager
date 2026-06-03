import os
import time
import requests
from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

    print(f"\n[ONLINE EXECUTION] Running connection sequence for: {profile_name}")

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

    # 2. Configure Cloud Driver with Advanced Anti-Fingerprinting
    options = Options()
    options.add_argument("--headless=new")  # Mandatory cloud layer
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")
    
    # Emulate real desktop behavior to reduce automated blocking risk
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    base_dir = os.getcwd()
    chrome_path = os.path.join(base_dir, ".render", "chrome", "chrome-linux64", "chrome")
    driver_path = os.path.join(base_dir, ".render", "chrome", "chromedriver-linux64", "chromedriver")

    options.binary_location = chrome_path
    chrome_service = Service(driver_path)

    try:
        print("[STEP 1] Starting Browser Engine...")
        driver = webdriver.Chrome(service=chrome_service, options=options)
        
        # Strip automated navigator flag signatures
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[STEP 2] Navigating to Instagram Auth Server...")
        driver.get("https://www.instagram.com/accounts/login/")
        
        # Use Explicit WebDriverWait instead of arbitrary sleep counters
        print("[STEP 3] Waiting for elements to resolve via DOM check...")
        wait = WebDriverWait(driver, 15)
        
        # Target the input name tags dynamically to handle layout shifts
        username_field = wait.until(EC.presence_of_element_rule((By.NAME, "username")))
        password_field = driver.find_element(By.NAME, "password")
        
        print("[STEP 4] Simulating human keystrokes...")
        for char in username:
            username_field.send_keys(char)
            time.sleep(0.04)
            
        for char in password:
            password_field.send_keys(char)
            time.sleep(0.04)
            
        print("[STEP 5] Clicking submit trigger button...")
        password_field.send_keys(Keys.ENTER)
        
        # Wait to verify if page transitions to the dashboard feed
        time.sleep(12) 
        
        final_url = driver.current_url
        print(f"[COMPLETE] Ended tracking route sequence at: {final_url}")
        driver.quit()
        
        if "login" not in final_url.lower():
            return redirect(url_for('index', status='success', account=profile_name, msg="Successfully Authenticated! Connected to live profile route."))
        else:
            return redirect(url_for('index', status='error', msg="Authentication failed. Instagram rejected the session or requested secondary verification."))

    except Exception as error:
        print(f"[CRITICAL FAILURE] Stopped processing layout: {error}")
        return redirect(url_for('index', status='error', msg="Elements failed to extract. The server's hosting footprint is triggering security checkpoints."))

if __name__ == '__main__':
    app.run(debug=True)

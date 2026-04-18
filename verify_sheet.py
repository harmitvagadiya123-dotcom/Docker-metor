
import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

def verify_google_sheet():
    print("[INFO] Starting Google Sheet Verification...")
    
    # 1. Load .env
    load_dotenv()
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME")
    creds_b64 = os.getenv("GOOGLE_SHEETS_CREDENTIALS_B64")
    
    if not all([sheet_id, sheet_name, creds_b64]):
        print("[ERROR] Missing required environment variables in .env")
        print(f"   GOOGLE_SHEET_ID: {'Set' if sheet_id else 'MISSING'}")
        print(f"   GOOGLE_SHEET_NAME: {'Set' if sheet_name else 'MISSING'}")
        print(f"   GOOGLE_SHEETS_CREDENTIALS_B64: {'Set' if creds_b64 else 'MISSING'}")
        return

    print(f"[DATA] Sheet ID: {sheet_id}")
    print(f"[DATA] Tab Name: {sheet_name}")

    # 2. Decode Credentials
    try:
        # Clean the string
        b64_str = creds_b64.strip().strip('"').strip("'")
        b64_str = "".join(b64_str.split())
        b64_str = b64_str.rstrip("=")
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += "=" * (4 - missing_padding)
            
        decoded = base64.b64decode(b64_str)
        creds_dict = json.loads(decoded)
        print(f"[OK] Credentials decoded successfully. Service Account: {creds_dict.get('client_email')}")
    except Exception as e:
        print(f"[ERROR] Failed to decode credentials: {e}")
        return

    # 3. Authenticate and Connect
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        print("[OK] Authentication with Google API successful.")
        
        # 4. Open Spreadsheet
        spreadsheet = client.open_by_key(sheet_id)
        print(f"[OK] Spreadsheet opened: '{spreadsheet.title}'")
        
        # 5. Check Tab
        worksheet = spreadsheet.worksheet(sheet_name)
        headers = worksheet.row_values(1)
        print(f"[OK] Tab '{sheet_name}' found.")
        print(f"[DATA] Headers found: {headers}")
        
        print("\n[SUCCESS] EVERYTHING LOOKS CORRECT! Your credentials and sheet settings are valid.")
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"[ERROR] Spreadsheet not found. Double-check the ID and ensure the service account {creds_dict.get('client_email')} has 'Editor' access.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"[ERROR] Worksheet '{sheet_name}' not found. Check the tab name (it is case-sensitive).")
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")

if __name__ == "__main__":
    verify_google_sheet()

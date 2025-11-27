from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import requests
import json
import google.generativeai as genai
import assemblyai as aai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# 1. CONFIGURE GEMINI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# 2. LOAD TRANSACTION DATA
DB_FILE = "suspicious_transactions.json"

def get_active_case():
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            # Find the first pending case
            for case in data:
                if case["status"] == "pending":
                    return case
            return data[0]
    except:
        return {}

def update_case_status(case_id, new_status):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        
        for case in data:
            if case["id"] == case_id:
                case["status"] = new_status
                
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"DB Error: {e}")

# 3. MURF VOICE (Authoritative)
def generate_murf_speech(text):
    MURF_API_KEY = os.getenv('MURF_AI_API_KEY')
    voice_id = "en-US-marcus" 
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "voice_id": voice_id,
        "style": "Promo",
        "multiNativeLocale": "en-US"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
             # Fallback
             payload["voice_id"] = "en-UK-ruby"
             retry = requests.post(url, headers=headers, data=json.dumps(payload))
             return retry.json().get('audioFile')
        return response.json().get('audioFile')
    except:
        return None

@router.get("/health")
async def health_check():
    return HTMLResponse(content="<h1>Fraud Alert System Active 🔒</h1>", status_code=200)

@router.post("/start-session")
async def start_session():
    case = get_active_case()
    if not case:
        return JSONResponse(content={"text": "No active alerts."})

    greeting = f"This is an urgent call from HDFC Bank Fraud Detection. Am I speaking with {case['userName']}?"
    
    return JSONResponse(content={
        "text": greeting,
        "audioUrl": generate_murf_speech(greeting),
        "case_data": case 
    })

# --- MAIN FRAUD AGENT LOGIC ---
@router.post("/chat-with-voice")
async def chat_with_voice(
    file: UploadFile = File(...), 
    current_state: str = Form(...)
):
    try:
        # A. SETUP
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        try:
            state = json.loads(current_state)
        except:
            state = {"verification_stage": "unverified", "case_status": "pending"}

        # Get the actual DB record
        case_record = get_active_case()
        REQUIRED_DIGITS = case_record['cardEnding'] # "4242"

        # B. TRANSCRIBE
        audio_data = await file.read()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        user_text = transcript.text or ""
        print(f"🔒 User Said: {user_text}")

        # --- C. STRICT SECURITY GATE (PYTHON LOGIC) ---
        # We override the LLM if the verification is incorrect.
        
        system_override = ""
        
        if state["verification_stage"] == "unverified":
            # Check if user text contains the required digits
            # We handle "4242", "4 2 4 2", "four two four two" logic vaguely here, 
            # but strictly checking for the number is safest.
            if REQUIRED_DIGITS in user_text.replace(" ", ""):
                print("✅ SECURITY PASS: Correct Digits Detected")
                state["verification_stage"] = "verified"
                system_override = "User PASSED verification. The state is now VERIFIED. Read the transaction details immediately."
            else:
                print("❌ SECURITY FAIL: Incorrect Digits")
                # We force the LLM to reject it
                system_override = f"User FAILED verification. They did NOT say {REQUIRED_DIGITS}. You MUST politely ask them to repeat the last 4 digits. Do NOT proceed."

        # D. SECURITY BRAIN (Gemini)
        system_prompt = f"""
        You are a Senior Fraud Analyst at HDFC Bank.
        
        CASE FILE:
        {json.dumps(case_record)}
        
        CURRENT STATE:
        Verification Stage: {state.get('verification_stage')}
        Case Status: {state.get('case_status')}
        
        USER SAID: "{user_text}"
        
        SYSTEM OVERRIDE INSTRUCTION: {system_override}
        
        PROTOCOL:
        1. If 'verification_stage' is 'unverified': 
           - Ask for last 4 digits of card ending in {case_record['cardEnding']}.
           - Do NOT discuss the transaction until verified.
        
        2. If 'verification_stage' is 'verified':
           - State: "I see a transaction at {case_record['transactionName']} for {case_record['transactionAmount']}. Did you authorize this?"
           - If User says YES: Mark 'safe'.
           - If User says NO: Mark 'fraudulent'.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "updated_state": {{
                "verification_stage": "unverified" | "verified",
                "case_status": "pending" | "safe" | "fraudulent"
            }},
            "reply": "Spoken response"
        }}
        """

        result = model.generate_content(
            system_prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        ai_resp = json.loads(result.text)
        new_state = ai_resp["updated_state"]
        agent_reply = ai_resp["reply"]
        
        print(f"🛡️ Analyst: {agent_reply}")

        # E. UPDATE DATABASE
        if new_state["case_status"] != "pending":
            update_case_status(case_record["id"], new_state["case_status"])
            print(f"✅ Case {case_record['id']} marked as {new_state['case_status']}")

        # F. AUDIO
        audio_url = generate_murf_speech(agent_reply)

        return {
            "user_transcript": user_text,
            "ai_text": agent_reply,
            "audio_url": audio_url,
            "updated_state": new_state
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
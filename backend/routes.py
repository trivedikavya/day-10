from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import requests
import json
import google.generativeai as genai
import assemblyai as aai
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

router = APIRouter()

# 1. CONFIGURE GOOGLE GEMINI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# DATA FILE
WELLNESS_FILE = "wellness_log.json"

# HELPER: Get the last check-in for context
def get_last_checkin():
    if not os.path.exists(WELLNESS_FILE):
        return None
    try:
        with open(WELLNESS_FILE, "r") as f:
            data = json.load(f)
            return data[-1] if data else None
    except:
        return None

# HELPER: Save new check-in
def save_checkin(entry):
    data = []
    if os.path.exists(WELLNESS_FILE):
        try:
            with open(WELLNESS_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []
    
    data.append(entry)
    with open(WELLNESS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@router.get("/health")
async def health_check():
    return HTMLResponse(content="<h1>Wellness Companion Running 🌿</h1>", status_code=200)

# --- SMART GREETING ROUTE ---
@router.post("/start-session")
async def start_session():
    """Generates a greeting based on past history."""
    last_entry = get_last_checkin()
    
    context_prompt = ""
    if last_entry:
        context_prompt = f"The user's last check-in was on {last_entry.get('date')}. They felt: '{last_entry.get('mood')}' and their goal was: '{last_entry.get('goals')}'. Reference this briefly."
    else:
        context_prompt = "This is the user's first session."

    system_prompt = f"""
    You are a supportive, grounded Health & Wellness Voice Companion.
    {context_prompt}
    
    Your goal: Greet the user warmly and ask how they are feeling today.
    Keep it short (1-2 sentences). Do NOT be a doctor. Be a friend.
    """
    
    try:
        # Generate greeting text
        result = model.generate_content(system_prompt)
        greeting_text = result.text

        # Convert to Audio
        MURF_API_KEY = os.getenv('MURF_AI_API_KEY')
        murf_url = "https://api.murf.ai/v1/speech/generate"
        murf_headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
        murf_data = {
            "text": greeting_text,
            "voice_id": "en-UK-ruby", 
            "style": "Conversational",
            "multiNativeLocale": "en-US"
        }
        murf_res = requests.post(murf_url, headers=murf_headers, data=json.dumps(murf_data))
        
        return JSONResponse(content={"text": greeting_text, "audioUrl": murf_res.json().get('audioFile')})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# --- MAIN CONVERSATION LOOP ---
@router.post("/chat-with-voice")
async def chat_with_voice(
    file: UploadFile = File(...), 
    current_state: str = Form(...) 
):
    try:
        # A. SETUP
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        murf_api_key = os.getenv('MURF_AI_API_KEY')
        
        # Parse State
        try:
            state_dict = json.loads(current_state)
        except:
            state_dict = {"mood": None, "energy": None, "goals": [], "is_complete": False}

        # B. TRANSCRIBE
        audio_data = await file.read()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        user_text = transcript.text or ""
        
        print(f"🗣️ User: {user_text}")

        # C. REASONING (The Wellness Brain)
        system_prompt = f"""
        You are a supportive Wellness Companion. You are NOT a doctor.
        Current Check-in State: {json.dumps(state_dict)}
        User just said: "{user_text}"

        OBJECTIVES:
        1. Extract 'mood' (how they feel), 'energy' (low/med/high/tired), and 'goals' (intentions for today).
        2. If fields are missing, ask for them gently.
        3. If the user shares a struggle, offer a VERY BRIEF, grounded reflection (e.g., "Maybe take a 5-min walk").
        4. If all fields (mood, energy, goals) are filled, set 'is_complete' to true and give a quick summary.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "updated_state": {{
                "mood": "string or null",
                "energy": "string or null",
                "goals": ["string"],
                "is_complete": boolean
            }},
            "reply": "Your warm, concise spoken response here."
        }}
        """

        result = model.generate_content(
            system_prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        ai_response = json.loads(result.text)
        updated_state = ai_response["updated_state"]
        companion_reply = ai_response["reply"]

        print(f"🌿 Companion: {companion_reply}")

        # D. SAVE DATA (If complete)
        if updated_state.get("is_complete") and not state_dict.get("is_complete"):
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "mood": updated_state["mood"],
                "energy": updated_state["energy"],
                "goals": updated_state["goals"],
                "summary": companion_reply
            }
            save_checkin(entry)
            print("✅ Wellness Log Updated")

        # E. TTS GENERATION
        murf_url = "https://api.murf.ai/v1/speech/generate"
        murf_headers = {"api-key": murf_api_key, "Content-Type": "application/json"}
        murf_data = {
            "text": companion_reply,
            "voice_id": "en-UK-ruby", 
            "style": "Conversational",
            "multiNativeLocale": "en-US"
        }
        murf_res = requests.post(murf_url, headers=murf_headers, data=json.dumps(murf_data))

        return {
            "user_transcript": user_text,
            "ai_text": companion_reply,
            "audio_url": murf_res.json().get('audioFile'),
            "updated_state": updated_state
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
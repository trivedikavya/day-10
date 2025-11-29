from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
import requests
import json
import google.generativeai as genai
import assemblyai as aai
from dotenv import load_dotenv
import commerce

load_dotenv()

router = APIRouter()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# HELPER: MURF VOICE
def generate_murf_speech(text):
    MURF_API_KEY = os.getenv('MURF_AI_API_KEY')
    voice_id = "en-US-natalie"
    
    # --- AUDIO FIX ---
    # Convert symbols to words so the TTS engine doesn't crash or go silent
    # Also remove parentheses as requested
    spoken_text = text.replace("₹", " Rupees ").replace("(", "").replace(")", "")
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": spoken_text,
        "voice_id": voice_id,
        "style": "Promo",
        "multiNativeLocale": "en-US"
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        if response.status_code != 200:
             # Fallback to Ruby if Natalie fails
             payload["voice_id"] = "en-UK-ruby"
             retry = requests.post(url, headers=headers, data=json.dumps(payload))
             return retry.json().get('audioFile')
        return data.get('audioFile')
    except:
        return None

@router.get("/health")
async def health_check():
    return HTMLResponse(content="<h1>Commerce Agent Active 🛍️</h1>", status_code=200)

@router.post("/start-session")
async def start_session():
    greeting = "Welcome to StyleStore. I can help you browse our collection or track an order. What are you looking for today?"
    return JSONResponse(content={
        "text": greeting,
        "audioUrl": generate_murf_speech(greeting)
    })

@router.post("/chat-with-voice")
async def chat_with_voice(
    file: UploadFile = File(...), 
    current_state: str = Form(...)
):
    try:
        aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        try:
            state = json.loads(current_state) 
        except:
            state = {"last_search_results": []}

        audio_data = await file.read()
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_data)
        user_text = transcript.text or ""
        print(f"🛒 User: {user_text}")

        # The Prompt instructs Gemini to act as the Shopping Assistant
        system_prompt = f"""
        You are a Voice Shopping Assistant for 'StyleStore'.
        
        TOOLS AVAILABLE (Mental Model):
        1. SEARCH: list_products(category, color, max_price)
        2. ORDER: create_order(product_id, quantity, size)
        3. HISTORY: get_last_order()
        
        CONTEXT:
        Last displayed products: {json.dumps(state.get('last_search_results', []))}
        
        USER SAID: "{user_text}"
        
        INSTRUCTIONS:
        1. Interpret Intent: SEARCH, ORDER, or HISTORY.
        2. Action:
           - SEARCH: Extract filters. output action="search".
           - ORDER: Match user words to 'Last displayed products'. output action="order".
           - HISTORY: output action="history".
        3. Response: Generate a polite, short reply. 
           IMPORTANT: Do NOT use parentheses like ( ) in your response text. Use commas or separate sentences instead. 
           Example: "I found a T-shirt for 500 Rupees." NOT "I found a T-shirt (500 Rupees)."
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "action": "search" | "order" | "history" | "chat",
            "search_filters": {{ "category": "...", "color": "...", "max_price": "..." }},
            "order_details": [ {{ "product_id": "...", "quantity": 1, "size": "..." }} ],
            "reply": "Spoken text"
        }}
        """

        result = model.generate_content(
            system_prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        ai_decision = json.loads(result.text)
        action = ai_decision.get("action")
        reply = ai_decision.get("reply")
        
        new_state_data = state.get('last_search_results', [])
        
        # Execute the chosen tool
        if action == "search":
            filters = ai_decision.get("search_filters")
            products = commerce.list_products(filters)
            new_state_data = products
            
            if products:
                # We build the reply purely for display/text, actively removing brackets for speech safety
                product_names = ", ".join([f"{p['name']} for {p['price']} Rupees" for p in products[:3]])
                reply = f"I found a few items: {product_names}. Do you want to buy any?"
            else:
                reply = "I couldn't find any products matching that description."

        elif action == "order":
            order_items = ai_decision.get("order_details")
            if order_items:
                order = commerce.create_order(order_items)
                reply = f"Order placed! Your Order ID is {order['order_id']}. Total is {order['total_amount']} Rupees."
            else:
                reply = "I'm not sure which item you want to buy. Could you clarify?"

        elif action == "history":
            last_order = commerce.get_last_order()
            if last_order:
                items_str = ", ".join([i['product_name'] for i in last_order['items']])
                reply = f"Your last order was for {items_str}, totaling {last_order['total_amount']} Rupees."
            else:
                reply = "You haven't placed any orders yet."

        print(f"🛍️ Assistant: {reply}")

        # GENERATE SPEECH (With cleaned text)
        audio_url = generate_murf_speech(reply)

        return {
            "user_transcript": user_text,
            "ai_text": reply,
            "audio_url": audio_url,
            "updated_state": {
                "last_search_results": new_state_data 
            }
        }

    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
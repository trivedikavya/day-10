import json
import random

# --- SCENARIOS LIST ---
SCENARIOS = [
    "You are a barista telling a customer their latte is a portal to another dimension.",
    "You are a time-travelling tour guide explaining TikTok to a peasant from 1400 AD.",
    "You are a cat trying to convince a dog to let you blame him for the broken vase.",
    "You are an alien tour guide pretending to be human but getting basic facts wrong.",
    "You are a waiter calmly explaining that the customer's soup is actually a magical potion."
]

def get_initial_state():
    return {
        "phase": "intro",        
        "player_name": "",
        "round": 0,
        "max_rounds": 3,         # Game ends after 3 rounds
        "current_scenario": "",
        "history": [] 
    }

def get_system_prompt(state, user_text):
    # SAFETY: Default to 'playing' if phase is weird
    phase = state.get("phase", "playing")
    
    # 1. INTRO PHASE
    if phase == "intro":
        return f"""
        You are the host of a chaotic improv game show called 'Improv Battle'.
        User Input: "{user_text}"
        
        GOAL:
        1. Extract name.
        2. Welcome them.
        3. Give FIRST Scenario: "{SCENARIOS[0]}"
        
        OUTPUT JSON:
        {{
            "reply": "Welcome [Name]! Your first scenario is: {SCENARIOS[0]}",
            "player_name": "extracted_name",
            "next_phase": "playing",
            "next_scenario": "{SCENARIOS[0]}"
        }}
        """

    # 2. PLAYING PHASE (Now includes Summary Logic)
    elif phase == "playing":
        current_round = state.get("round", 0)
        max_r = state.get("max_rounds", 3)
        history = state.get("history", [])
        
        # Logic: Are we moving to the next round OR ending?
        next_r_index = current_round + 1
        is_game_over = next_r_index >= max_r
        
        # SAFETY: Cycle scenarios if we run out
        safe_scenario_idx = next_r_index % len(SCENARIOS)
        next_scenario = SCENARIOS[safe_scenario_idx]

        if not is_game_over:
            # --- NORMAL ROUND ---
            return f"""
            Host of 'Improv Battle'. 
            SCENARIO: "{state.get('current_scenario')}"
            ACT: "{user_text}"
            
            GOAL:
            1. Rate performance (be witty/funny).
            2. Give next scenario: "{next_scenario}".
            
            OUTPUT JSON:
            {{
                "reply": "Haha! Good one. Next scenario: {next_scenario}...",
                "next_phase": "playing",
                "next_scenario": "{next_scenario}"
            }}
            """
        else:
            # --- FINAL ROUND (SUMMARY) ---
            return f"""
            Host of 'Improv Battle'. THIS IS THE FINAL ROUND.
            SCENARIO: "{state.get('current_scenario')}"
            ACT: "{user_text}"
            PREVIOUS HISTORY: {json.dumps(history)}
            
            GOAL:
            1. Rate the FINAL performance briefly.
            2. IMMEDIATELY segue into a Grand Summary of the player's entire game style based on History + Final Act.
            3. Say "Game Over" and thank them.
            
            OUTPUT JSON:
            {{
                "reply": "Nice finish! Looking back at your game, you are a [Adjective] improviser. You loved [Topic]... Thanks for playing Improv Battle!",
                "next_phase": "ended",
                "next_scenario": ""
            }}
            """

    # 3. ENDED PHASE (Just in case)
    elif phase == "ended":
        return f"""
        The game is over. User said: "{user_text}".
        Just politely say the show is done.
        
        OUTPUT JSON:
        {{
            "reply": "The show is over! Refresh to play again.",
            "next_phase": "ended",
            "next_scenario": ""
        }}
        """
    
    return "You are a helpful AI. Just say 'Error in game state, let's reset'."
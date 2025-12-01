document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const joinScreen = document.getElementById("join-screen");
  const gameStage = document.getElementById("game-stage");
  const controlsFooter = document.getElementById("controls-footer");
  
  const agentText = document.getElementById("agent-text");
  const playerText = document.getElementById("player-text");
  const playerBubble = document.getElementById("player-bubble");
  
  const micBtn = document.getElementById("mic-btn");
  const startBtn = document.getElementById("start-btn");
  const statusLabel = document.getElementById("status-label");
  const agentAudio = document.getElementById("agent-audio");
  
  const scenarioCard = document.getElementById("scenario-card");
  const scenarioText = document.getElementById("scenario-text");
  const roundBadge = document.getElementById("round-badge");

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  let currentState = { phase: "intro" };

  // --- 1. START CONNECTION ---
  startBtn.addEventListener("click", async () => {
    // UI Transition
    joinScreen.classList.add("hidden");
    gameStage.classList.remove("hidden");
    gameStage.classList.add("flex");
    controlsFooter.classList.remove("hidden");
    controlsFooter.classList.add("flex");
    
    statusLabel.textContent = "Connecting...";

    try {
      const res = await axios.post("http://localhost:5000/start-session");
      
      // Initial Response (Ask Name)
      agentText.textContent = res.data.text;
      
      if (res.data.initial_state) currentState = res.data.initial_state;
      
      handleAudio(res.data);
      
    } catch (err) {
      console.error(err);
      agentText.textContent = "Error connecting to studio server.";
    }
  });

  // --- 2. MIC LOGIC ---
  micBtn.addEventListener("click", async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          // UI: Thinking State
          statusLabel.textContent = "Thinking...";
          statusLabel.classList.add("text-purple-400");
          micBtn.innerHTML = "✨"; 
          micBtn.disabled = true;
          micBtn.classList.remove("pulse-record");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          formData.append("current_state", JSON.stringify(currentState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            // 1. Show Player Text
            if (res.data.user_transcript) {
                playerText.textContent = `"${res.data.user_transcript}"`;
                playerBubble.classList.remove("hidden");
            }

            // 2. Show Host Text
            agentText.textContent = res.data.ai_text;

            // 3. Update State & UI
            if (res.data.updated_state) {
                currentState = res.data.updated_state;
                renderGameUI(currentState);
            }

            // 4. Handle Audio (Playback or Fallback)
            handleAudio(res.data);

          } catch (err) {
            console.error(err);
            agentText.textContent = "Technical difficulties on set. Please retry.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        statusLabel.textContent = "Recording...";
        statusLabel.classList.add("text-red-400");
        micBtn.innerHTML = "⏹️"; 
        micBtn.classList.add("pulse-record");

      } catch (err) {
        alert("Microphone denied. Please check browser settings.");
      }

    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  // --- HELPERS ---

  function renderGameUI(state) {
    // Show Scenario Card if playing
    if (state.current_scenario && state.phase !== "summary" && state.phase !== "ended" && state.phase !== "intro") {
        scenarioCard.classList.remove("hidden");
        scenarioText.textContent = `"${state.current_scenario}"`;
    } else {
        scenarioCard.classList.add("hidden");
    }

    // Show Round Badge
    if (state.phase === "playing") {
        roundBadge.classList.remove("hidden");
        const current = (state.round || 0) + 1;
        const max = state.max_rounds || 3;
        roundBadge.textContent = `ROUND ${current} / ${max}`;
    } else {
        roundBadge.classList.add("hidden");
    }
  }

  function handleAudio(data) {
      if (data.audioUrl) {
          playAudio(data.audioUrl);
      } else {
          // Browser TTS Fallback
          speakNative(data.ai_text || data.text);
      }
  }

  function playAudio(url) {
    agentAudio.src = url;
    statusLabel.textContent = "Speaking...";
    statusLabel.classList.remove("text-purple-400", "text-red-400");
    statusLabel.classList.add("text-cyan-400");
    
    agentAudio.play();
    agentAudio.onended = resetMicUI;
    agentAudio.onerror = resetMicUI;
  }

  function speakNative(text) {
      console.log("Using Browser TTS");
      statusLabel.textContent = "Speaking...";
      statusLabel.classList.add("text-cyan-400");
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.1; 
      utterance.onend = resetMicUI;
      window.speechSynthesis.speak(utterance);
  }

  function resetMicUI() {
    statusLabel.textContent = "Ready";
    statusLabel.classList.remove("text-purple-400", "text-red-400", "text-cyan-400");
    statusLabel.classList.add("text-slate-500");
    
    micBtn.disabled = false;
    micBtn.innerHTML = "🎙️";
    micBtn.classList.remove("pulse-record");
  }
});
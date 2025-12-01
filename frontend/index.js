document.addEventListener("DOMContentLoaded", () => {
  const agentText = document.getElementById("agent-text");
  const playerText = document.getElementById("player-text");
  const playerBubble = document.getElementById("player-bubble");
  
  const micBtn = document.getElementById("mic-btn");
  const startBtn = document.getElementById("start-btn");
  const statusLabel = document.getElementById("status-label");
  const agentAudio = document.getElementById("agent-audio");
  
  // UI Elements
  const scenarioCard = document.getElementById("scenario-card");
  const scenarioText = document.getElementById("scenario-text");
  const roundBadge = document.getElementById("round-badge");

  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  let currentState = { phase: "intro" };

  async function initSession() {
    try {
      const res = await axios.post("http://localhost:5000/start-session");
      agentText.textContent = res.data.text;
      
      // Reset Player UI
      playerBubble.classList.add("hidden");
      
      if (res.data.initial_state) currentState = res.data.initial_state;
      if (res.data.audioUrl) playAudio(res.data.audioUrl);
      
      renderGameUI(currentState);
    } catch (err) {
      console.error(err);
      agentText.textContent = "Error connecting to studio server.";
    }
  }
  
  startBtn.addEventListener("click", () => location.reload());
  
  // Start immediately
  initSession();

  // --- MIC LOGIC ---
  micBtn.addEventListener("click", async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          // UI Updates while processing
          statusLabel.textContent = "Thinking...";
          micBtn.innerHTML = "✨"; // Sparkles while AI thinks
          micBtn.disabled = true;
          micBtn.classList.remove("pulse-mic");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          formData.append("current_state", JSON.stringify(currentState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            // 1. Show User Transcript
            if (res.data.user_transcript) {
                playerText.textContent = `"${res.data.user_transcript}"`;
                playerBubble.classList.remove("hidden");
            }

            // 2. Show AI Response
            agentText.textContent = res.data.ai_text;

            // 3. Update Game State (Rounds, Scenarios)
            if (res.data.updated_state) {
                currentState = res.data.updated_state;
                renderGameUI(currentState);
            }

            // 4. Play Audio
            if (res.data.audio_url) {
              playAudio(res.data.audio_url);
            } else {
              resetMicUI();
            }

          } catch (err) {
            console.error(err);
            agentText.textContent = "Technical difficulties on set. Please retry.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        statusLabel.textContent = "On Air";
        micBtn.innerHTML = "⏹️"; 
        micBtn.classList.add("pulse-mic");

      } catch (err) {
        alert("Microphone denied.");
      }

    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  // --- UI RENDERER ---
  function renderGameUI(state) {
    // 1. Show/Hide Scenario Stage
    // We show the scenario card if there is text AND we are not in the ending summary
    if (state.current_scenario && state.phase !== "summary" && state.phase !== "ended") {
        scenarioCard.classList.remove("hidden");
        scenarioText.textContent = `"${state.current_scenario}"`;
    } else {
        scenarioCard.classList.add("hidden");
    }

    // 2. Update Round Badge
    if (state.phase === "playing") {
        roundBadge.classList.remove("hidden");
        // Rounds are 0-indexed in code, so display +1
        const current = (state.round || 0) + 1;
        const max = state.max_rounds || 3;
        roundBadge.textContent = `Round ${current} / ${max}`;
    } else if (state.phase === "summary" || state.phase === "ended") {
        roundBadge.textContent = "Game Over";
        roundBadge.classList.remove("hidden");
        roundBadge.classList.replace("text-purple-300", "text-red-400");
    } else {
        roundBadge.classList.add("hidden");
    }
  }

  function playAudio(url) {
    agentAudio.src = url;
    statusLabel.textContent = "Speaking...";
    agentAudio.play();
    agentAudio.onended = resetMicUI;
    agentAudio.onerror = resetMicUI;
  }

  function resetMicUI() {
    statusLabel.textContent = "Ready";
    micBtn.disabled = false;
    micBtn.innerHTML = "🎙️";
    micBtn.classList.remove("pulse-mic");
  }
});
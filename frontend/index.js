document.addEventListener("DOMContentLoaded", () => {
  const agentText = document.getElementById("agent-text");
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
      if (res.data.initial_state) currentState = res.data.initial_state;
      if (res.data.audioUrl) playAudio(res.data.audioUrl);
      renderGameUI(currentState);
    } catch (err) {
      console.error(err);
      agentText.textContent = "Error connecting to server.";
    }
  }
  
  startBtn.addEventListener("click", () => location.reload());
  initSession();

  micBtn.addEventListener("click", async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        
        mediaRecorder.onstop = async () => {
          statusLabel.textContent = "Processing...";
          micBtn.innerHTML = "⏳";
          micBtn.disabled = true;
          micBtn.classList.remove("pulse-mic");

          const blob = new Blob(audioChunks, { type: 'audio/webm' });
          const formData = new FormData();
          formData.append("file", blob, "recording.webm");
          formData.append("current_state", JSON.stringify(currentState));

          try {
            const res = await axios.post("http://localhost:5000/chat-with-voice", formData);

            agentText.textContent = res.data.ai_text;
            if (res.data.updated_state) {
                currentState = res.data.updated_state;
                renderGameUI(currentState);
            }
            if (res.data.audio_url) playAudio(res.data.audio_url);
            else resetMicUI();

          } catch (err) {
            console.error(err);
            agentText.textContent = "Sorry, connection issue.";
            resetMicUI();
          }
        };

        mediaRecorder.start();
        isRecording = true;
        statusLabel.textContent = "Listening...";
        micBtn.innerHTML = "⏹️"; 
        micBtn.classList.add("pulse-mic");

      } catch (err) { alert("Microphone denied."); }
    } else {
      mediaRecorder.stop();
      isRecording = false;
    }
  });

  function renderGameUI(state) {
    // 1. Show/Hide Scenario
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
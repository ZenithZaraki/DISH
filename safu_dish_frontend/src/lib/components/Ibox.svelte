<script>
  import { runCommand } from '../api.js';
  import { fade, fly } from 'svelte/transition';
  import { tick } from 'svelte'; // ✅ Required for DOM sync before scrolling

  let message = '';
  let history = [];
  let inputBox;
  let chatCommandKey = null;
  let chatHistoryEl;
  let showScrollButton = false;
  let instructionTextValue = ''; // 🧠 Optional shared instruction value
  let rollingContextEnabled = true;
  // === SESSION MANAGEMENT ===
  let sessionId = crypto.randomUUID();   // unique chat session
  const MAX_HISTORY = 50;                // UI safety limit

  // === 🧩 Attempt Dynamic Import for Instruction Store ===
  (async () => {
    try {
      const { instructionText } = await import('$lib/instructionStore.js');
      instructionText.subscribe(value => instructionTextValue = value);
      console.log('[CHATBOX] Instruction store linked.');
    } catch {
      console.warn('[CHATBOX] Instruction store not found — running without it.');
    }
  })();

  // --- Fetch manifest on startup ---
  async function fetchManifest() {
    try {
      const res = await fetch(`/api/manifest/IMAS`);
      const manifest = await res.json();

      if (manifest?.main?.imas_generate_reply?.routing_key) {
        chatCommandKey = manifest.main.imas_generate_reply.routing_key + ".0";
      } else {
        console.error("❌ No imas_generate_reply key found in manifest:", manifest);
        chatCommandKey = "IMAS.main.imas_generate_reply.0"; // fallback
      }

      console.log("✅ Using chat command key:", chatCommandKey);
    } catch (err) {
      console.error("❌ Failed to fetch DISH manifest:", err);
      chatCommandKey = "IMAS.main.imas_generate_reply.0"; // fallback
    }
  }

  fetchManifest();

  // --- Smooth scroll helper ---
  function smoothScrollToBottom() {
    if (chatHistoryEl) {
      chatHistoryEl.scrollTo({
        top: chatHistoryEl.scrollHeight,
        behavior: 'smooth'
      });
    }
  }

  // --- Track scroll position ---
  function handleScroll() {
    if (!chatHistoryEl) return;
    const threshold = 60;
    const distanceFromBottom =
      chatHistoryEl.scrollHeight - chatHistoryEl.scrollTop - chatHistoryEl.clientHeight;
    showScrollButton = distanceFromBottom > threshold;
  }

  // --- Send message handler ---
  async function sendMessage() {
    if (!message.trim()) return;

    const userMessage = message;
    history = [...history, { role: 'user', content: userMessage }];
    // Prevent UI history from growing forever
    if (history.length > MAX_HISTORY) {
      history = history.slice(-MAX_HISTORY);
    }
    await tick();
    smoothScrollToBottom();

    message = '';
    if (inputBox) inputBox.style.height = 'auto';

    if (!chatCommandKey) {
      history = [...history, { role: 'assistant', content: 'Error: chat command not initialized.' }];
      await tick();
      smoothScrollToBottom();
      return;
    }

    const placeholderIndex = history.length;
    history = [...history, { role: 'assistant', content: '__thinking__' }];
    await tick();
    smoothScrollToBottom();

    if (chatHistoryEl) chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    const url = '/api/modules/IMAS/imas/respond?stream=true';

    // Remove UI placeholders like __thinking__
    const cleanedHistory = history.filter(
      msg => !msg.content.startsWith('__')
    );

    // Context control
    const historyToSend = rollingContextEnabled ? cleanedHistory : [];

    const payload = {
      session_id: sessionId,
      message: userMessage,
      history: historyToSend,   // ← use the toggle
      ...(instructionTextValue ? { instruction: instructionTextValue } : {})
    };

    try {
      console.log("➡️ [CHATBOX] Sending request:", {
        url,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload
      });

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      console.log("⬅️ [CHATBOX] Raw response:", res);

      if (!res.ok) {
        const errorText = await res.text();
        console.error(`❌ [CHATBOX] Response not OK: ${res.status} ${res.statusText}`);
        console.error("❌ [CHATBOX] Error body:", errorText);
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }

      // ✅ Stream response as text instead of JSON
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let partial = '';
      let fullReply = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullReply += chunk;
        partial += chunk;

        history[placeholderIndex] = { role: 'assistant', content: partial };
        history = [...history];
        await tick();
        smoothScrollToBottom();
      }

      console.log("[CHATBOX] Final full reply:", fullReply);

      // === 🧼 CLEANUP SECTION ===
      fullReply = fullReply
        .replaceAll(/^NOVA:\s?/gm, '')
        .replace(/(Critique|Summary|ORIGINAL RESPONSE|Refined):\n[\s\S]+$/gi, '')
        .trim();

      history[placeholderIndex] = { role: 'assistant', content: fullReply };
      history = [...history];
      await tick();
      smoothScrollToBottom();

    } catch (err) {
      console.error("❌ [CHATBOX] Chat request failed:", err);
      history[placeholderIndex] = { role: 'assistant', content: 'Error: could not get reply.' };
      history = [...history];
      await tick();
      smoothScrollToBottom();
    }
  }

  function autoResize(event) {
    const el = event.target;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
</script>

<div class="chat-container">
  <!-- CHAT HISTORY -->
  <div
    class="chat-history"
    id="chat-history"
    bind:this={chatHistoryEl}
    on:scroll={handleScroll}
  >
    {#each history as msg, i (i)}
      <div
        class={`message ${msg.role}`}
        in:fly={{ y: 10, duration: 300, opacity: 0 }}
        out:fade={{ duration: 200 }}
      >
        {#if msg.content === '__thinking__'}
          <div class="thinking-dots">
            <span></span><span></span><span></span>
          </div>
        {:else}
          <p>{msg.content}</p>
        {/if}
      </div>
    {/each}
  </div> <!-- ✅ closes chat-history -->

  <!-- SCROLL BUTTON -->
  {#if showScrollButton}
    <button
      class="scroll-to-bottom"
      on:click={smoothScrollToBottom}
      in:fly={{ y: 20, duration: 200, opacity: 0 }}
      out:fade={{ duration: 150 }}
    >
      ↓
    </button>
  {/if}

  <!-- INPUT BAR -->
  <div class="chat-input-wrapper">
    
    <textarea
      id="chatInput"
      bind:this={inputBox}
      bind:value={message}
      on:input={autoResize}
      on:keydown={handleKeydown}
      placeholder="Speak, mortal..."
      class="chat-input"
      rows="2"
    ></textarea>

    <div class="send-column">

      <button class="chat-send-button" on:click={sendMessage}>
        Send
      </button>

      <div class="context-toggle">

        <span class="toggle-label tooltip">
          CTX
          <span class="tooltip-text">
            Rolling Context keeps previous messages in memory so the AI
            understands the full conversation. Turn it off for isolated
            prompts during testing or benchmarking.
          </span>
        </span>

        <label class="toggle-switch">
          <input type="checkbox" bind:checked={rollingContextEnabled} />
          <span class="slider"></span>
        </label>

      </div>

    </div>
  </div> <!-- ✅ closes chat-input-wrapper -->
</div> <!-- ✅ closes chat-container -->

<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Exo+2:wght@800;900&family=Oxanium:wght@700;800&display=swap" rel="stylesheet">
<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  .chat-container {
    display: grid;
    grid-template-rows: 1fr auto; /* ← scrollable area + fixed input bar */
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  h1, h2, h3 {
    margin: 0;
    padding: 0;
  }

  .chat-title {
    font-size: 1.6rem;
    margin: 0.1rem 0;
    padding: 0;
    line-height: 1;
    text-align: center;
  }

  .chat-history {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
    border-radius: 8px;
    min-height: 0;
    height: 25.5vw;
    width: flex;
    margin: 0;
    position: center;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #252424;
    font-family: 'OCR A Extended', monospace;
    text-shadow: 0 0 .5px #111, 0 0 5px #111;
    box-shadow: inset 0 0 12px #111;
    color: #0ff;
    scrollbar-width: thin;
    scroll-behavior: smooth;
  }

  .chat-history::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    background: repeating-linear-gradient(
      to bottom,
      rgba(0, 255, 255, 0.04) 0px,
      rgba(0, 255, 255, 0.02) 1px,
      transparent 2px,
      transparent 3px
    );
    mix-blend-mode: overlay;
  }

  .chat-history::-webkit-scrollbar {
    width: 6px;
  }

  .chat-history::-webkit-scrollbar-thumb {
    background-color: #0ff;
    border-radius: 4px;
  }

  /* 🔵 Animated thinking dots with glow */
  .thinking-dots {
    display: flex;
    gap: 6px;
    padding: 4px 0;
    align-items: center;
  }

  .thinking-dots span {
    width: 8px;
    height: 8px;
    background-color: #0ff;
    border-radius: 50%;
    display: inline-block;
    animation: bounceGlow 1.4s infinite ease-in-out;
    box-shadow: 0 0 6px #0ff, 0 0 12px #0ff;
  }

  .thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
  .thinking-dots span:nth-child(2) { animation-delay: -0.16s; }
  .thinking-dots span:nth-child(3) { animation-delay: 0s; }

  @keyframes bounceGlow {
    0%, 80%, 100% { 
      transform: scale(0.6);
      opacity: 0.4;
      box-shadow: 0 0 3px #0ff;
    }
    40% { 
      transform: scale(1.2);
      opacity: 1;
      box-shadow: 0 0 10px #0ff, 0 0 20px #0ff;
    }
  }

  .scroll-to-bottom {
    position: absolute;
    bottom: 3rem;
    right: 1.5rem;
    background-color: #111;
    color: #0ff;
    border: 1px solid #0ff;
    border-radius: 35%;
    width: 0.5rem;
    height: 1.3rem;
    font-size: 1.4rem;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    align-items: center;       /* vertically center */
    justify-content: center;   /* horizontally center */
    line-height: 1;  
    box-shadow: 0 0 6px #0ff, 0 0 12px #0ff;
    transition: transform 0.2s ease, box-shadow 0.3s ease;
    opacity: 0.9;
    z-index: 2;
  }

  .scroll-to-bottom:hover {
    transform: scale(1.1);
    box-shadow: 0 0 10px #0ff, 0 0 13px #0ff;
  }

  .chat-input-wrapper {
    display: flex;
    justify-content: center;
    margin-bottom: 0rem;
    padding: .5rem;
    gap: 0.25rem;
    border-radius: 7px;
    border-top: .5px solid #0ff2;
    border-right: 1px solid #0ff2;
    background-color: #111;
    flex-shrink: 0;
    align-items: flex-end;
    z-index: 1;
    box-shadow: 0 -1px 4px #0ff2;
  }

  .chat-input {
    flex-grow: 1;
    padding: 0.5rem;
    background-color: #252424;
    color: #0ff;
    border: none;
    outline: none;
    border-radius: 6px;
    font-family: 'OCR A Extended', monospace;
    line-height: 1.4rem;
    overflow-y: auto;
    font-size: 1.1rem;
    text-shadow: 0 0 1px #0ff, 0 0 7px #0ff;
    box-shadow: inset 0 0 10px #111;
    min-height: calc(1.4em * 2);
    max-height: calc(1.4em * 8);
    resize: none;  
  }

  .chat-send-button {
    background-color: #111;
    border: 1px solid #0ff;
    padding: 0.75rem .75rem;
    margin-bottom: .6rem;
    border-radius: 6px;
    font-weight: bold;
    cursor: pointer;
    transition:
      box-shadow 0.3s ease,
      color 0.3s ease,
      border-color 0.3s ease;
  }

  .chat-send-button:hover,
  .chat-send-button:focus {
    outline: none;
    color: #0ff;
    border-color: #0ff;
    box-shadow: 0 0 8px #0ff, 0 0 16px #0ff;
    background-color: #000;
  }

  .chat-send-button:active {
    transform: scale(0.92);
    box-shadow: 0 0 4px #0ff inset;
  }

  .context-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 3px;
    font-size: 0.75rem;
    font-family: 'OCR A Extended', monospace;
    color: #0ff;
    opacity: 0.85;
  }

  .toggle-label {
    font-size: 0.75rem;
    letter-spacing: 1px;
  }

  /* Hide the default checkbox */
  .toggle-switch input {
    display: none;
  }

  /* Switch track */
  .slider {
    width: 32px;
    height: 14px;
    background: #111;
    border: 1px solid #0ff;
    border-radius: 10px;
    position: relative;
    display: inline-block;
    box-shadow: inset 0 0 6px #0ff3;
    transition: all 0.25s ease;
  }

  /* Switch knob */
  .slider::before {
    content: "";
    width: 10px;
    height: 10px;
    background: #0ff;
    border-radius: 50%;
    position: absolute;
    left: 2px;
    top: 1px;
    transition: transform 0.25s ease;
    box-shadow: 0 0 4px #0ff;
  }

  /* ON state */
  .toggle-switch input:checked + .slider {
    background: #001f1f;
    box-shadow: 0 0 6px #0ff, inset 0 0 6px #0ff5;
  }

  .toggle-switch input:checked + .slider::before {
    transform: translateX(16px);
    box-shadow: 0 0 6px #0ff, 0 0 12px #0ff;
  }

  .message.assistant {
    padding: 0.1rem 0.2rem;
    font-size: 1.19rem;
    line-height: 1.5;
    max-width: 85%;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: 'OCR A Extended', monospace;
    border-left: 2px solid rgba(0, 255, 255, 0.292);
    margin-bottom: 0.2rem;
    align-self: flex-start;
    text-align: left;
  }

  .message.assistant p::after {
    content: '▌';
    animation: blink 1.1s steps(1, start) infinite;
    color: #0ff;
    margin-left: 2px;
  }
  @keyframes blink {
    50% { opacity: 0; }
  }

  .message.user {
    padding: 0.1rem 0.2rem;
    font-size: 1.19rem;
    line-height: 1.5;
    max-width: 85%;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: 'OCR A Extended', monospace;
    border-right: 2px solid #0ff;
    margin-bottom: 0.2rem;
    align-self: flex-end;
    text-align: left;
  }

  /* Tooltip container */
  .tooltip {
    position: relative;
    cursor: help;
  }

  /* Tooltip bubble */
  .tooltip-text {
    visibility: hidden;
    opacity: 0;
    width: 260px;

    background: #111;
    color: #0ff;

    border: 1px solid #0ff;
    border-radius: 6px;

    padding: 8px;
    font-size: 0.75rem;
    line-height: 1.3;

    position: absolute;
    bottom: 140%;
    left: -70px;
    transform: translateX(-50%);

    box-shadow: 0 0 8px #0ff4;
    text-shadow: none;

    transition: opacity 0.2s ease;
    z-index: 9999;
  }

  /* Tooltip arrow */
  .tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);

    border-width: 6px;
    border-style: solid;
    border-color: #0ff transparent transparent transparent;
  }

  /* Show tooltip on hover */
  .tooltip:hover .tooltip-text {
    visibility: visible;
    opacity: 1;
  }

  /* Ensure footer hugs the bottom */
  .footer {
    margin-top: 0 !important;
    padding-top: 0px;
  }

</style>

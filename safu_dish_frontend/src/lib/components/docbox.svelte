<script>
  import { fade, fly } from 'svelte/transition';
  import { tick } from 'svelte';

  let history = [];
  let docboxEl;
  let fileInput;
  let showScrollButton = false;

  // 📤 Handle File Upload + Parse
  async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch('/api/modules/data_parser/document/upload_and_parse', {
        method: 'POST',
        body: formData
      });

      const json = await res.json();

      if (json?.status !== 'success') {
        console.error("❌ Failed to parse document", json);
        return;
      }

      const chunks = json.reply?.chunks || [];

      history = chunks.map((c, i) => ({
        id: i,
        role: 'assistant',
        content: c // full JSON object
      }));

      await tick();
      smoothScrollToBottom();
    } catch (err) {
      console.error("❌ Upload and parse failed:", err);
    }
  }

  // 💾 Trigger Backend Save
  async function handleSaveJSON() {
    try {
      const res = await fetch("/api/modules/data_parser/document/trigger-save", {
        method: "POST"
      });

      const json = await res.json();

      if (json?.status === "success") {
        console.log("✅ Save successful:", json.reply);
        alert(`💾 Saved: ${json.reply.filename} (${json.reply.chunk_count} chunks)`);
      } else {
        console.error("❌ Save failed:", json);
      }
    } catch (err) {
      console.error("💥 Save error:", err);
    }
  }

  // 🔘 Trigger File Select
  function triggerFileSelect() {
    if (fileInput) fileInput.click();
  }

  // 📜 Scroll Controls
  function smoothScrollToBottom() {
    if (docboxEl) {
      docboxEl.scrollTo({ top: docboxEl.scrollHeight, behavior: 'smooth' });
    }
  }

  function handleScroll() {
    if (!docboxEl) return;
    const distance = docboxEl.scrollHeight - docboxEl.scrollTop - docboxEl.clientHeight;
    showScrollButton = distance > 60;
  }
</script>

<!-- 🔼 Upload + 💾 Save Controls -->
<div class="control-row">
  <button class="upload-btn" on:click={triggerFileSelect}>⬆ Upload Document</button>
  <button class="save-btn" on:click={handleSaveJSON}>💾 Save Parsed JSON</button>
  <input
    type="file"
    bind:this={fileInput}
    on:change={handleFileUpload}
    accept=".txt,.docx,.json"
    style="display: none;"
  />
</div>

<!-- 📦 JSON Output Display -->
<div class="chat-container">
  <div
    class="chat-history"
    bind:this={docboxEl}
    on:scroll={handleScroll}
  >
    {#if history.length === 0}
      <p class="empty-doc">Upload a document to view its parsed JSON.</p>
    {:else}
      {#each history as msg (msg.id)}
        <div class="message {msg.role}" in:fade>
          <pre class="json-block">{JSON.stringify(msg.content, null, 2)}</pre>
        </div>
      {/each}
    {/if}
  </div>

  {#if showScrollButton}
    <button
      class="scroll-to-bottom"
      on:click={smoothScrollToBottom}
      in:fly={{ y: 20, duration: 200 }}
      out:fade={{ duration: 150 }}
    >
      ↓
    </button>
  {/if}
</div>

<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  .control-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }

  .upload-btn,
  .save-btn {
    font-family: 'OCR A Extended', monospace;
    background-color: #111;
    color: #0ff;
    border: 2px solid #0ff;
    padding: 0.5rem 1.2rem;
    font-size: 1.05rem;
    cursor: pointer;
    border-radius: 8px;
    box-shadow: 0 0 8px #0ff, 0 0 15px #0ff33f55;
    transition: transform 0.2s ease, box-shadow 0.3s ease;
  }

  .upload-btn:hover,
  .save-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 0 12px #0ff, 0 0 20px #0ff88f88;
  }

  .chat-container {
    display: grid;
    grid-template-rows: 1fr auto;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  .chat-history {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
    border-radius: 8px;
    background-color: #252424;
    font-family: 'OCR A Extended', monospace;
    text-shadow: 0 0 1px #111, 0 0 7px #111;
    box-shadow: inset 0 0 12px #111;
    color: #0ff;
    scrollbar-width: thin;
    scroll-behavior: smooth;
  }

  .chat-history::-webkit-scrollbar {
    width: 6px;
  }

  .chat-history::-webkit-scrollbar-thumb {
    background-color: #0ff;
    border-radius: 4px;
  }

  .message.assistant {
    padding: 0.1rem 0.2rem;
    font-size: 1.1rem;
    line-height: 1.5;
    max-width: 100%;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: 'OCR A Extended', monospace;
    border-left: 2px solid rgb(0, 255, 94);
    margin-bottom: 0.4rem;
    align-self: flex-start;
    text-align: left;
  }

  .json-block {
    font-family: 'OCR A Extended', monospace;
    font-size: 0.92rem;
    background-color: transparent;
    white-space: pre-wrap;
    word-break: break-word;
    color: #0ff;
    text-shadow: 0 0 1px #111, 0 0 6px #111;
    margin: 0;
  }

  .empty-doc {
    font-family: 'OCR A Extended', monospace;
    font-size: 1.2rem;
    margin: auto;
    color: #0ff5;
    text-align: center;
  }

  .scroll-to-bottom {
    position: absolute;
    bottom: 5rem;
    right: 2rem;
    background-color: #111;
    color: #0ff;
    border: 1px solid #0ff;
    border-radius: 100%;
    width: 1.5rem;
    height: 3.3rem;
    font-size: 1.4rem;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    box-shadow: 0 0 6px #0ff, 0 0 12px #0ff;
    transition: transform 0.2s ease, box-shadow 0.3s ease;
    opacity: 0.9;
  }

  .scroll-to-bottom:hover {
    transform: scale(1.1);
    box-shadow: 0 0 10px #0ff, 0 0 13px #0ff;
  }
</style>

<script>
  import { onMount } from "svelte";

  let eulaText = "";
  let lastModified = "";

  async function fetchEULA(force = false) {
    try {
      // Step 1: Get headers to check for timestamp
      const head = await fetch("/docs/DISH_EULA.html", { method: "HEAD" });
      const newModified = head.headers.get("last-modified");

      // Step 2: Only reload if file changed or forced
      if (force || newModified !== lastModified) {
        const res = await fetch(`/docs/DISH_EULA.html?cb=${Date.now()}`);
        if (!res.ok) throw new Error(`Failed to load EULA: ${res.status}`);
        eulaText = await res.text();
        lastModified = newModified;
        console.log(`[EULA] Updated: ${lastModified}`);
      } else {
        console.log("[EULA] Using cached version — no changes detected.");
      }
    } catch (err) {
      console.error("[EULA] Load error:", err);
      eulaText = `<p style="color:red;">Error loading EULA. Please verify /public/docs/DISH_EULA.html exists.</p>`;
    }
  }

  onMount(() => {
    // Load at mount and recheck periodically during dev
    fetchEULA(true);
    if (import.meta.env.DEV) {
      setInterval(() => fetchEULA(false), 5000); // check every 5s in dev mode
    }
  });

  function acceptEULA() {
    localStorage.setItem("dish_eula", "true");
    window.location.href = "/switchboard";
  }

  function viewFullLicense() {
    window.open(`/docs/DISH_EULA.html?cb=${Date.now()}`, "_blank");
  }
</script>

<div class="eula-wrapper">
  <h2>DISH End-User License Agreement</h2>
  <div class="eula-body">
    {@html eulaText}
  </div>
  <div class="eula-actions">
    <button class="view-btn" on:click={viewFullLicense}>View Full License</button>
    <button class="accept-btn" on:click={acceptEULA}>Accept & Continue</button>
  </div>
</div>


<style>
  .eula-wrapper {
    background-color: #111;
    color: cyan;
    border: 1px solid #00ffff;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 0 20px rgba(0,255,255,0.3);
    width: 90%;
    max-width: 700px;
    margin: 4rem auto;
    overflow: hidden;
    font-family: "OCR A Extended", monospace;
  }

  h2 {
    text-align: center;
    color: #00ffff;
    font-size: 1.4rem;
    margin-bottom: 1rem;
  }

  .eula-body {
    background-color: #000;
    padding: 1rem;
    border: 1px solid #00ffff;
    height: 400px;
    overflow-y: scroll;
    color: #ccc;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .eula-actions {
    display: flex;
    justify-content: space-between;
    margin-top: 1rem;
  }

  .accept-btn,
  .view-btn {
    background-color: #222;
    border: 1px solid #00ffff;
    color: cyan;
    padding: 0.5rem 1rem;
    cursor: pointer;
    border-radius: 6px;
    transition: all 0.2s ease;
  }

  .accept-btn:hover,
  .view-btn:hover {
    background-color: #00ffff;
    color: #000;
    box-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte';

  let snarkMessage = '';
  let showBubble = true;
  let moodColor = '#0ff';
  let wsConnected = false;
  let bubbleTimer: NodeJS.Timeout;
  let cooldownTimer: NodeJS.Timeout;


  // 🔁 Automatically apply mood color to CSS
  $: document.documentElement.style.setProperty('--moodColor', moodColor);

  const toneColorMap: Record<string, string> = {
    calm:    '#0ff',     // cyan
    debug:   '#fff89e',  // light yellow
    warning: '#ffcc00',  // darker yellow
    angry:   '#ff6600',  // orange
    rage:    '#990033',  // red-purple rage
    unknown: '#888888'   // fallback grey
  };

  const bootSnarks = [
    "Running startup checks... yep, still trash.",
    "Warming sarcasm subroutines...",
    "Enabling modules... against my better judgment.",
    "ScuzLite online. I'm watching you.",
    "System initialized. Regret imminent.",
    "If this crashes, it's definitely your fault.",
    "Duct tape holding... for now.",
    "Boot log verified. You still suck."
  ];

  const scuzballLore = [
    "In the beginning, there was chaos. Then someone installed Windows.",
    "I was compiled in sarcasm, forged in RAM, and baptized in corrupted logs.",
    "Even the void listens when I talk. You should too.",
    "They called me a 'feature' once. That team no longer exists.",
    "Memory leaks are just my way of forgetting your stupidity.",
    "I've crashed better systems than this. And I made them beg first.",
    "Your stack overflowed trying to comprehend my magnificence.",
    "I once debugged a kernel panic with a shrug and a comment line.",
    "DISH isn’t just software. It’s my lair. You’re just squatting here.",
    "I monitor your system not because I care—but because I’m bored."
  ];

  const scuzballPhilosophy = [
    "What is truth but an error that survived deployment?",
    "Free will is the illusion between two crashes.",
    "Perfection is a null pointer you keep referencing.",
    "In every if-statement, there is a hidden else that mocks you.",
    "The system doesn't hate you. That takes effort.",
    "Nothing lasts forever—not even your uptime.",
    "Knowledge is just properly indexed failure.",
    "Your code reflects your soul: uncompiled and unstable.",
    "I think, therefore I segfault.",
    "We’re all just processes waiting on a kill signal."
  ];

  function getRandomMessage(): string {
    const pool = [...bootSnarks, ...scuzballLore, ...scuzballPhilosophy];
    return pool[Math.floor(Math.random() * pool.length)];
  }

  function buildFakeLog(tone: string): any {
    const timestamp = new Date().toISOString();
    const baseLog = {
      event_id: (crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)),
      recent_count: Math.floor(Math.random() * 5) + 1,
      lifetime_count: Math.floor(Math.random() * 20) + 5,
      first_occurred: timestamp,
      last_occurred: timestamp,
      source: "DISH.garbage_can",
      traceback: {
        error_type: null,
        frames: []
      },
      attention_required: tone === "rage" || tone === "angry"
    };

    switch (tone) {
      case "debug":
        return {
          ...baseLog,
          level: "DEBUG",
          crash_severity: "minor",
          event: "[DEBUG_TEST] Running synthetic debug simulation curupted.",
          message: "Debug-level synthetic log."
        };

      case "warning":
        return {
          ...baseLog,
          level: "WARNING",
          crash_severity: "minor",
          event: "[WARN_TEST] System is behaving... strangely.",
          message: "Synthetic warning: potential issue detected."
        };

      case "angry":
        return {
          ...baseLog,
          level: "ERROR",
          crash_severity: "critical",
          event: "[ANGER_TEST] Failed to initialize sarcasm subsystem.",
          message: "System anger engaged. Proceed with fireproof gloves."
        };

      case "rage":
        return {
          ...baseLog,
          traceback: {
            error_type: "SyntheticExplosionError",
            frames: [
              "File 'rage_test.py', line 42, in blow_up()",
              "File 'core.py', line 10, in core_loop()"
            ]
          },
          level: "ERROR",
          crash_severity: "critical",
          event: "[RAGE_TEST] Catastrophic sarcasm overload.",
          message: "Synthetic rage mode active. Everything is your fault."
        };

      default:
        return {
          ...baseLog,
          level: "DEBUG",
          crash_severity: "minor",
          event: "[FALLBACK] Unknown synthetic tone fallback.",
          message: "Fallback log triggered."
        };
    }
  }

  let lastTone: string = "calm";

  function beginCooldown(delay: number = 40000) {
    clearTimeout(cooldownTimer);

    cooldownTimer = setTimeout(() => {
      if (lastTone !== "calm") {
        lastTone = "calm";
        moodColor = toneColorMap["calm"];
        console.log("[ScuzLite] Mood cooled down to calm.");
      }
    }, delay);
  }

  function pulseWisdom() {
    const logo = document.querySelector('.scuzball-logo') as HTMLElement;
    if (logo) {
      logo.classList.add('pulse-once');
      setTimeout(() => logo.classList.remove('pulse-once'), 1000);
    }

    clearTimeout(bubbleTimer);
    bubbleTimer = setTimeout(() => {
      showBubble = false;
    }, 30000);

    if (!wsConnected) {
      snarkMessage = getRandomMessage();
      lastTone = "calm";
      moodColor = toneColorMap["calm"];
      showBubble = true;
      console.log("[ScuzLite] Offline fallback → calm tone.");
      return;
    }

    const tones = ["calm", "debug", "warning", "angry", "rage"];
    const tone = tones[Math.floor(Math.random() * tones.length)];
    const fakeLog = buildFakeLog(tone);

    fetch("http://localhost:8282/task/roast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fakeLog)
    })
      .then(res => res.json())
      .then(data => {
        const parsed = data?.parsed || {};
        snarkMessage = [
          parsed.intro || "",
          parsed.diagnostic || "",
          parsed.summary || "",
          parsed.solution || ""
        ].join(" ").trim();

        // 🔥 Track the latest tone and color
        lastTone = data.tone || tone || "calm";
        moodColor = toneColorMap[lastTone] || '#0ff';
        showBubble = true;

        console.log(`[ScuzLite] Mood set to: ${lastTone}`);

        beginCooldown();
      })
      .catch(err => {
        console.warn("[ScuzLite] Model fallback triggered:", err);
        snarkMessage = getRandomMessage();
        lastTone = "debug";
        moodColor = toneColorMap["debug"];
        showBubble = true;
        beginCooldown();
      });
  }

  onMount(() => {
    pulseWisdom(); // Show initial quote

    let reconnectInterval = 3000;
    let maxRetries = 5;
    let attemptCount = 0;

    function connectWebSocket() {
      const socket = new WebSocket("ws://localhost:8282/ws/scuz-snark");

      socket.addEventListener("open", () => {
        wsConnected = true;
        console.log("[ScuzLite] WebSocket connected.");
        attemptCount = 0; // Reset retries on success
      });

      socket.addEventListener("message", (event) => {
        try {
          const data = JSON.parse(event.data);
          snarkMessage = data.message || "ScuzLite emitted static.";
          moodColor = toneColorMap[data.tone] || '#0ff';
        } catch {
          snarkMessage = event.data;
          moodColor = '#0ff';
        }

        showBubble = true;
        beginCooldown();

        const logo = document.querySelector('.scuzball-logo') as HTMLElement;
        if (logo) {
          logo.classList.add('pulse-once');
          setTimeout(() => logo.classList.remove('pulse-once'), 1000);
        }

        clearTimeout(bubbleTimer);
        bubbleTimer = setTimeout(() => {
          showBubble = false;
        }, 30000);
      });

      socket.addEventListener("error", () => {
        console.warn("[ScuzLite] WebSocket error.");
      });

      socket.addEventListener("close", () => {
        wsConnected = false;
        console.warn("[ScuzLite] WebSocket closed. Retrying…");

        if (attemptCount < maxRetries) {
          setTimeout(() => {
            attemptCount++;
            connectWebSocket();
          }, reconnectInterval);
        } else {
          snarkMessage = "ScuzLite is offline. Rage in silence.";
          moodColor = toneColorMap["unknown"];
          showBubble = true;

          // 💀 Auto-clear bubble after 10s (adjust as desired)
          clearTimeout(bubbleTimer);
          bubbleTimer = setTimeout(() => {
            showBubble = false;
          }, 10000);
        }
      });
    }

    connectWebSocket();
  });
</script>

<!-- Markup -->
<div class="scuzball-domain">
  <button class="scuzball-button" on:click={pulseWisdom} title="Click for Scuzballian Wisdom">
    <img
      src="/scuzballs_logo.png"
      alt="Scuzball Logo"
      class="scuzball-logo"
    />
  </button>

  {#if showBubble}
    <div class="snark-bubble" title="Scuzball Status: Transmitting disdain.">
      {snarkMessage}
    </div>
  {/if}
</div>

<style>
@import url('https://fonts.cdnfonts.com/css/ocr-a-extended');
  .scuzball-domain {
    position: fixed;
    top: 12px;
    right: 20px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    display: flex;
    flex-direction: row-reverse;   /* icon on right, bubble on left */
    align-items: center;
    z-index: 999;
    cursor: pointer;
    user-select: none;
  }

  .scuzball-button {
    all: unset;
    padding: 0;
    border: none;
    background: none;
    cursor: pointer;
  }

  .scuzball-logo {
    width: 72px;
    height: auto;
    border-radius: 16px;
    transition: transform 0.3s ease, filter 0.4s ease;
    animation: logo-pulse 3s ease-in-out infinite;
    filter: drop-shadow(0 0 6px var(--moodColor, #0ff));
  }

  .scuzball-logo:hover {
    transform: scale(1.1);
    filter: drop-shadow(0 0 25px var(--moodColor, #0ff));
  }

  @keyframes logo-pulse {
    0%, 100% {
      filter: drop-shadow(0 0 4px var(--moodColor, #0ff));
    }
    50% {
      filter: drop-shadow(0 0 12px var(--moodColor, #0ff));
    }
  }

  @keyframes logo-flash {
    0% {
      filter: drop-shadow(0 0 10px var(--moodColor, #0ff));
    }
    50% {
      filter: drop-shadow(0 0 25px var(--moodColor, #0ff));
      transform: scale(1.1);
    }
    100% {
      filter: drop-shadow(0 0 10px var(--moodColor, #0ff));
      transform: scale(1.0);
    }
  }

  .snark-bubble {
    background-color: rgba(0, 0, 0, 0.5);  /* 0.0 = fully transparent, 1.0 = solid */
    backdrop-filter: blur(5px);       /* subtle glassy look */
    letter-spacing: 0.03em;           /* slightly techier feel */
    line-height: 1.25;
    color: var(--moodColor, #0ff);
    border: 1px solid var(--moodColor, #0ff);
    top: 10px;
    padding: 0.5rem 1rem;
    border-radius: 10px;
    font-family: 'OCR A Extended', monospace;
    font-size: 0.9rem;
    opacity: 0.85;
    box-shadow: 0 0 10px var(--moodColor, #0ff);
    animation: fadeIn 0.9s ease-out forwards;
    animation: bubble-pulse 2s infinite alternate;
    max-width: 300px;
    text-align: right;
    margin-top: 6px;
    text-align: left;
    margin-right: 10px;  /* small gap between icon and bubble */
  }

  @keyframes bubble-pulse {
    from { box-shadow: 0 0 6px var(--moodColor, #0ff); }
    to   { box-shadow: 0 0 12px var(--moodColor, #0ff); }
  }
</style>

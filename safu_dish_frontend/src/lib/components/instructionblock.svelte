<script lang="ts">
  import { onMount } from 'svelte';
  let instruction = '';
  let storeLinked = false;

  // 🧠 Try to link with shared store dynamically
  onMount(async () => {
    try {
      const { instructionText } = await import('$lib/instructionStore.js');
      instructionText.subscribe(value => (instruction = value || ''));
      $: instructionText.set(instruction);
      storeLinked = true;
      console.log('[InstructionBlock] Linked to instruction store.');
    } catch (err) {
      console.warn('[InstructionBlock] No instruction store found — running isolated.');
    }
  });

  function handleInput(e: Event) {
    instruction = (e.target as HTMLTextAreaElement).value;
    // If linked to store, propagate live
    if (storeLinked) {
      import('$lib/instructionStore.js')
        .then(({ instructionText }) => instructionText.set(instruction))
        .catch(() => {});
    }
  }
</script>

<div class="instruction-block">
  <label>Instruction Context</label>
  <textarea
    placeholder="Enter persistent system instruction..."
    bind:value={instruction}
    on:input={handleInput}
    rows="5"
  ></textarea>

  {#if storeLinked}
    <p class="status">Synced with DISH runtime.</p>
  {:else}
    <p class="status warn">⚠️ Running isolated — store not linked.</p>
  {/if}
</div>
<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Exo+2:wght@800;900&family=Oxanium:wght@700;800&display=swap" rel="stylesheet">
<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  .instruction-block {
    display: flex;
    flex-direction: column;
    background-color: #111;
    border-radius: 8px;
    box-shadow: inset 0 0 12px #000, 0 0 8px #0ff2;
    border: 1px solid rgba(0, 255, 255, 0.2);
    padding: 0.5rem;
    margin-top: 0.2rem;
    margin-bottom: 0.5rem;
    font-family: 'Audiowide', sans-serif;
    color: cyan;
  }

  label {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  textarea {
    background-color: #252424;
    color: #0ff;
    border: none;
    outline: none;
    border-radius: 6px;
    padding: 0.75rem;
    font-family: 'OCR A Extended', monospace;
    font-size: 0.95rem;
    resize: vertical;
    min-height: 18rem;
    line-height: 1.4;
    text-shadow: 0 0 2px #111;
    box-shadow: inset 0 0 10px #000;
    width: 95%;            /* expand to fill nearly the whole diag panel */
    max-width: 520px;      /* wider than default (was 400px) */
    align-self: center;    /* centers it horizontally */
  }

  textarea:focus {
    box-shadow: 0 0 10px #0ff, 0 0 20px #0ff;
  }

  .status {
    font-size: 0.85rem;
    margin-top: 0.2rem;
    margin-bottom: 0.0rem;
    padding-bottom: 0rem;
    opacity: 0.8;
    color: #0ff;
    text-align: center;
  }

  .status.warn {
    color: #ff9;
    opacity: 0.7;
  }
</style>

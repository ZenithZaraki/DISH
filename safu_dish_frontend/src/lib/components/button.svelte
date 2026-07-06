<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let control;
  export let payload: Record<string, any> = {}; // 🔥 Explicit payload

  const dispatch = createEventDispatcher();

  const handleClick = async () => {
    if (!control?.routing_key) {
      console.warn('⚠️ No valid routing_key for this control:', control);
      return;
    }

    try {
      const response = await fetch('/api/run-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: control.routing_key,
          value: payload
        })
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ Command executed:', result);

      dispatch('trigger', result.result ?? result);
    } catch (err) {
      console.error('❌ Command execution failed:', err);
      dispatch('trigger', { error: err.message || 'Execution failed' });
    }
  };
</script>

{#if control?.routing_key}
  <button on:click={handleClick}>
    {control.text || 'Submit'}
  </button>
{:else}
  <button disabled style="opacity: 0.5; cursor: not-allowed;">
    ⚠️ Invalid Control
  </button>
{/if}

<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  button {
    padding: 0.65rem .85rem;
    background-color: #111;
    color: #ccc;
    border: 1px solid #0ff;
    border-radius: 7px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    font-family: 'OCR A Extended', monospace;
    transition: 
      box-shadow 0.3s ease,
      color 0.3s ease,
      border-color 0.3s ease;
  }

  button:hover,
  button:focus {
    outline: none;
    color: #0ff;
    border-color: #0ff;
    box-shadow: 0 0 8px #0ff, 0 0 16px #0ff;
    background-color: #000;
    transform: translateY(-3px);
  }

  button:active {
    transform: scale(0.92);
    box-shadow: 0 0 4px #0ff inset;
  }
</style>
<script lang="ts">
  import { onMount } from 'svelte';
  export let control;
  export let result;

  const label = control?.text || control?.label || 'Output';

  function formatResult(value) {
    if (!value || typeof value !== 'object') return value ?? 'N/A';

    return Object.entries(value)
      .map(([key, val]) => {
        const formatted = typeof val === 'object' && val !== null
          ? JSON.stringify(val)
          : JSON.stringify(val);
        return `"${key}": ${formatted}`;
      })
      .join('\n');
  }

  const fullValue = formatResult(result ?? control?.value);
  let streamedValue = '';
  let index = 0;
  const speed = 35; // ms per char

  onMount(() => {
    const interval = setInterval(() => {
      if (index < fullValue.length) {
        streamedValue += fullValue[index];
        index++;
      } else {
        clearInterval(interval);
      }
    }, speed);
  });

  console.debug('[ReadOnly] Streamed with:', { label, fullValue });
</script>

{#if control}
  <div class="read-only">
    <label>{label}</label>
    <pre class="value">{streamedValue}</pre>
  </div>
{:else}
  <div class="read-only invalid">⚠️ Invalid Control</div>
{/if}

<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  .read-only {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    margin-top: 0.75rem;
    background-color: #252424;
    box-shadow: inset 0 0 18px #111;
    border: none;
    border-radius: 6px;
    padding: 1rem;
    color: #0ff;
    font-family: 'OCR A Extended', monospace;
    text-align: left;
  }

  .read-only label {
    font-family: 'OCR A Extended', monospace;
    text-shadow: 0 0 1px #0ff, 0 0 5px #0ff;
    font-size: 1.5rem;
    font-weight: 650;
    color: cyan;
    opacity: 0.9;
  }

  .value {
    font-size: 0.90rem;
    font-weight: 500;
    color: cyan;
    white-space: pre-wrap;
    word-break: break-word;
    width: 100%;
    text-shadow: 0 0 1px #0ff, 0 0 5px #0ff;
  }

  .read-only.invalid {
    opacity: 0.6;
    font-style: italic;
    color: cyan;
  }
</style>

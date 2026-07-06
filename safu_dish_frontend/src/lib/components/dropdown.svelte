<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { tick } from 'svelte';

  export let control;
  export let value = '';
  export let options: string[] = [];
  export let action_key = ''; // Routing key to trigger when button is clicked
  export let resultOutput = ''; // Parent sets this

  const dispatch = createEventDispatcher();
  let routedOptions = [];

  onMount(async () => {
    if (!action_key && control?.routing_key) {
      action_key = control.routing_key;
    }

    if (control?.values_source) {
      try {
        const res = await fetch("http://127.0.0.1:8000" + control.values_source);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        const rawOptions = data.models || data;

        routedOptions = rawOptions.map((option) => ({
          value: option,
          label: option,
        }));

        if (routedOptions.length > 0) {
          value = routedOptions[0].value;
        }
      } catch (err) {
        console.error(`❌ Dropdown fetch failed for ${control.routing_key}:`, err);
      }
    } else if (control?.values?.length > 0) {
      routedOptions = control.values.map((val) => ({
        value: val,
        label: val,
      }));

      value = routedOptions[0].value;
    }
  });

  function handleChange(event) {
    value = event.target.value;
  }

  function handleLoadClick() {
    if (!action_key || !value) {
      console.warn("⚠️ Missing action_key or value.");
      return;
    }

    dispatch('trigger', {
      command: action_key,
      value: { path: value },
      status: 'pending'
    });
  }

let streamedOutput = '';
let outputIndex = 0;

$: if (resultOutput) {
  streamedOutput = '';
  outputIndex = 0;
  streamResult();
}

async function streamResult() {
  await tick(); // ensure DOM is ready
  const chars = resultOutput.split('');
  const minDelay = 10;  // 🔧 faster base delay
  const maxDelay = 40; // 🔧 tighter upper bound

  function typeNextChar() {
    if (outputIndex < chars.length) {
      streamedOutput += chars[outputIndex++];
      setTimeout(typeNextChar, Math.random() * (maxDelay - minDelay) + minDelay);
    }
  }

  typeNextChar();
}
</script>

<div class="dropdown">
  <label>{control.name}</label>
  <select bind:value={value} on:change={handleChange}>
    {#each routedOptions as opt}
      <option value={opt.value}>{opt.label}</option>
    {/each}
  </select>

  {#if action_key}
    <button on:click={handleLoadClick}>
      {control.text || 'Load'}
    </button>
  {/if}

  {#if resultOutput}
    <textarea
    readonly
    rows="10"
    class="textarea"
>{streamedOutput}</textarea>
  {/if}
</div>

<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');

  select {
    background-color: #000;
    font-size: 1.1rem;
    color: cyan;
    border: 1px solid #0ff;
    padding: 0.5rem;
    border-radius: 6px;
    font-family: 'OCR A Extended';
  }

  button {
    padding: 0.60rem .80rem;
    background-color: #111;
    color: #ccc;
    border: 1px solid #0ff;
    border-radius: 5px;
    font-size: 1.3rem;
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
  }

  .dropdown {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  textarea {
    width: 100%;
    resize: vertical;
    background-color: #252424;
    box-shadow: inset 0 0 18px #111;
    outline: none;
    border: none;
    border-radius: 6px;
    color: #0ff;
    font-family: 'OCR A Extended', monospace;
    text-align: left;
    font-size: 0.90rem;
    font-weight: 500;
    text-shadow: 0 0 1px #0ff, 0 0 5px #0ff;
  }

  label {
    font-family: 'OCR A Extended', monospace;
    font-size: 1.2rem;
    font-weight: bold;
    color: cyan;
    margin-bottom: 0.25rem;
    text-align: center;
    text-shadow: 0 0 2px #0ff;
  }
</style>



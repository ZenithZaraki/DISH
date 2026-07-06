<script>
  import { onMount } from 'svelte';
  export let control;

  let checked = control?.default || false;

  const handleChange = async () => {
    console.log("💡 Toggle clicked. State is now:", checked);

    try {
      const res = await fetch('/run-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: control.routing_key,
          value: { state: checked }
        })
      });

      const json = await res.json();
      console.log("✅ Backend response:", json);
    } catch (err) {
      console.error("❌ Backend call failed:", err);
    }
  };
</script>

<div class="toggle-wrapper">
  <label class="switch">
    <input type="checkbox" bind:checked on:change={handleChange} />
    <span class="slider"></span>
  </label>
  <span class="label-text">{control.name || 'Toggle'}</span>
</div>

<style>
  .toggle-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: 'OCR A Extended', monospace;
    color: cyan;
  }

  .switch {
    position: relative;
    display: inline-block;
    width: 50px;
    height: 28px;
  }

  .switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    cursor: pointer;
    top: 0; left: 0;
    right: 0; bottom: 0;
    background-color: #222;
    border: 1px solid #0ff;
    transition: 0.3s ease;
    border-radius: 34px;
    box-shadow: inset 0 0 6px #0ff;
  }

  .slider::before {
    position: absolute;
    content: "";
    height: 20px;
    width: 20px;
    left: 4px;
    bottom: 3.5px;
    background-color: cyan;
    transition: 0.3s ease;
    border-radius: 50%;
    box-shadow: 0 0 6px cyan;
  }

  input:checked + .slider {
    background-color: #0ff3;
  }

  input:checked + .slider::before {
    transform: translateX(22px);
  }

  .label-text {
    font-size: 1.1rem;
    text-shadow: 0 0 1px #0ff, 0 0 4px #0ff;
  }
</style>


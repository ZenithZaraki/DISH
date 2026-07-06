<script>
  // Accept the registry from the parent
  export let registry = {};

  // Import runCommand from centralized API layer
  import { runCommand } from '$lib/api';

  // Toggle handler for module switches
  function handleToggle(key, mod) {
    const newValue = !mod.enabled;

    runCommand({
      command: 'toggle_module',
      value: {
        module: key,
        enabled: newValue
      }
    })
      .then(response => {
        console.log(`✅ Toggled ${key}:`, response);
        mod.enabled = newValue; // optimistic update
      })
      .catch(err => {
        console.error(`❌ Failed to toggle ${key}:`, err);
        alert(`Error toggling module "${mod.name}"`);
      });
  }
</script>

<div class="grid">
  {#each Object.entries(registry) as [key, mod]}
    <div class="module-entry">
      <label title={`Are you *sure* you trust ${mod.display_name || mod.name}? I wouldn’t.`}>
        <input
          type="checkbox"
          checked={mod.enabled}
          disabled={mod.locked}
          on:change={() => handleToggle(key, mod)}
        />
        {mod.display_name || mod.name}
      </label>
    </div>
  {/each}
</div>

<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
    justify-items: center;
  }

  .module-entry {
    padding: 1rem;
    border: 1px solid #0ff;
    border-radius: 10px;
    background-color: #111;
    color: cyan;
    font-weight: bold;
    font-size: 1.2rem;
    font-family: 'OCR A Extended', monospace;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .module-entry:hover {
    transform: translateY(-3px);
  }

  input[type="checkbox"] {
    transform: scale(1.6);
    accent-color: cyan;
  }

  input[type="checkbox"]:disabled + label {
    opacity: 0.5;
  }
</style>

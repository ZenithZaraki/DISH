<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import { componentMap } from '$stores/componentMap';
  import { modules, selectedModuleId, selectedSidebarControls } from '$stores/modules';
  import { runCommand } from '$lib/api';

  const dispatch = createEventDispatcher();

  let loadedComponents: Record<string, any> = {};
  let commandResults: Record<string, any> = {};
  let selectedValues: Record<string, string> = {};

  function changeModule(event) {
    const selected = event.target.value;
    dispatch('selectModule', selected);
    selectedModuleId.set(selected);
  }

  async function loadComponent(type: string) {
    if (loadedComponents[type]) return loadedComponents[type];
    const entry = componentMap[type];
    if (!entry?.path) return null;
    try {
      const mod = await import(/* @vite-ignore */ entry.path);
      loadedComponents[type] = mod.default;
      return mod.default;
    } catch (err) {
      console.error(`Sidebar ❌ Failed to load ${type}:`, err);
      return null;
    }
  }

  async function handleCommand(control, payload = {}) {
    const routingKey = control?.routing_key;
    if (!routingKey) return;

    try {
      const result = await runCommand({ command: routingKey, value: payload });
      commandResults[routingKey] =
        result?.status === 'executed'
          ? result.result
          : { error: result?.status || 'Unknown backend issue' };
      await tick();
    } catch (err) {
      commandResults[routingKey] = { error: err.message || 'Execution error' };
    }
  }

  function handleDropdownChange(control, event) {
    const value = event.target.value;
    selectedValues[control.routing_key] = value;
    handleCommand(control, { selected: value });
  }
</script>

<div class="sidebar-ui">
  <!-- Module Selector -->
  <h2>APM Selection:</h2>
  <select on:change={changeModule} bind:value={$selectedModuleId}>
    <option value="switchboard">Switchboard</option>
    {#each $modules as mod}
      <option value={mod.id} title={mod.id}>
        {mod.display_name || mod.id}
      </option>
    {/each}
  </select>

  <!-- Dynamic Controls -->
  {#if $selectedSidebarControls}
    {#each Object.entries($selectedSidebarControls) as [group, controls]}
      <div class="group-block">
        <h3>{group}</h3>
        {#each controls as control (control.routing_key)}
          <div class="control-block">
            {#await loadComponent(control.type) then Component}
              {#if Component}
                <svelte:component
                  this={Component}
                  control={control}
                  value={selectedValues[control.routing_key]}
                  result={commandResults[control.routing_key]}
                  on:trigger={(e) => handleCommand(control, e.detail || {})}
                  on:change={(e) => control.type === 'dropdown' && handleDropdownChange(control, e)}
                />
              {/if}
            {/await}
          </div>
        {/each}
      </div>
    {/each}
  {:else}
    <div class="no-tools">
      <em>No sidebar tools for this module.</em>
    </div>
  {/if}
</div>
<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Exo+2:wght@800;900&family=Oxanium:wght@700;800&display=swap" rel="stylesheet">
<style>
@import url('https://fonts.cdnfonts.com/css/ocr-a-extended');
.sidebar-ui {
  font-family: 'Audiowide', sans-serif;
  margin-top: 0rem;
  padding-right: 1rem;
  padding-left: 1rem;
  padding-bottom: .1rem;
  color: cyan;
  height: 100%;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #0ff transparent;
}

.h2 {
margin-top: .1rem;
padding-top: 0rem;
padding-bottom: 0rem;
}

select {
  width: 90%;
  margin-top: 0rem;
  margin-bottom: .3rem;
  font-family: 'OCR A Extended', monospace;
  font-size: 1.1rem;
  background-color: #000;
  color: cyan;
  border: 1px solid #0ff;
  padding-top: 0%;
  padding: 0.4rem;
  border-radius: 6px;
}

select:hover,
select:focus {
  outline: none;
  color: #0ff;
  border-color: #0ff;
  box-shadow: 0 0 8px #0ff, 0 0 16px #0ff;
  background-color: #000;
  transform: translateY(-3px);
}

.group-block {
  margin-top: 1rem;
}

h3 {
  font-family: 'Audiowide', sans-serif;
  margin-bottom: 0.5rem;
  font-size: 1.2rem;
  color: #0ff;
  border-bottom: 1.3px solid #0ff3;
  padding-bottom: 0.5rem;
}

.control-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-top: .3rem; 
  margin-bottom: 1rem;
}

.no-tools {
  color: #777;
  text-align: left;
  font-style: italic;
  margin-top: 2rem;
}
</style>



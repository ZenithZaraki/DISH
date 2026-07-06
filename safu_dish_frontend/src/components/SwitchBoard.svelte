<script>
  import SwitchPanel from './SwitchPanel.svelte';
  import { modules, selectedModuleId } from '$stores/modules';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();
  let showSwitchBoard = false;

  function changeModule(event) {
    dispatch('selectModule', event.target.value);
    selectedModuleId.set(event.target.value);
  }

  function toggleSwitchBoard() {
    showSwitchBoard = !showSwitchBoard;
  }
</script>

<div class="sidebar-container">
  <div class="module-select">
    <label for="module">Module:</label>

    {#if $modules.length}
      <select id="module" on:change={changeModule} bind:value={$selectedModuleId}>
        {#each $modules as mod}
          <option value={mod.id}>{mod.display_name}</option>
        {/each}
      </select>
    {:else}
      <div class="no-modules">No modules found in registry.</div>
    {/if}

    <button class="toggle-button" on:click={toggleSwitchBoard}>
      {showSwitchBoard ? 'Hide Switchboard' : 'Show Switchboard'}
    </button>
  </div>

  {#if showSwitchBoard}
    <div class="switchboard-wrapper">
      <SwitchPanel registry={$modules} />
    </div>
  {/if}
</div>

<style>
  .sidebar-container {
    padding: 1rem;
    color: cyan;
    background-color: black;
    height: 100%;
    width: 100%;
    overflow-y: visible;
  }

  .module-select {
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    max-width: 300px;
    width: 90%;
    margin-left: auto;
    margin-right: auto;
  }

  label {
    font-size: 1rem;
    margin-bottom: 0.3rem;
    font-weight: 600;
    color: cyan;
    text-align: center;
  }

  select {
    width: 90%;
    padding: 0.4rem 0.6rem;
    font-size: 0.95rem;
    background-color: #000;
    color: cyan;
    border: 1px solid #0ff;
    border-radius: 6px;
    outline: none;
    appearance: none;
  }

  .toggle-button {
    margin-top: 0.5rem;
    padding: 0.3rem 0.6rem;
    background-color: cyan;
    color: black;
    font-weight: bold;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    width: 90%;
  }

  .toggle-button:hover {
    background-color: #0ff;
  }

  .no-modules {
    color: #888;
    font-style: italic;
    text-align: center;
    margin-top: 0.5rem;
  }

  .switchboard-wrapper {
    margin-top: 1rem;
    padding: 0.5rem;
    border-top: 1px dashed #0ff;
  }
</style>


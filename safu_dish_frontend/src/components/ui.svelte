<script lang="ts">
  import { selectedMainControls, selectedDiagControls, selectedModuleControls } from '$stores/modules';
  import MainPanel from './MainPanel.svelte';
  import DiagPanel from './DiagPanel.svelte';
  import ModuleRenderer from './ModuleRenderer.svelte';
</script>

{#if $selectedModuleControls === undefined}
  <div class="fallback">
    <h2>Awaiting Manifest</h2>
    <p>Scuzball is flipping through dusty archives for this one.</p>
  </div>

{:else if $selectedMainControls?.length > 0 || $selectedDiagControls?.length > 0}
  <div class="zoned-layout">
    <div class="main-panel">
      <MainPanel />
    </div>
    <div class="diag-panel">
      <DiagPanel />
    </div>
  </div>

{:else if $selectedModuleControls?.length > 0}
  <ModuleRenderer controls={$selectedModuleControls} />

{:else}
  <div class="fallback">
    <h2>Scuzball Disapproves</h2>
    <p>No controls found in the manifest for this module.</p>
    <p>It’s possible the module is just a useless husk, like your last attempt at adulthood.</p>
  </div>
{/if}

<style>
  .fallback {
    text-align: center;
    padding: 2rem;
    color: #ccc;
  }

  .fallback h2 {
    color: cyan;
    text-shadow: 0 0 4px cyan;
    margin-bottom: 1rem;
  }

  .zoned-layout {
    display: flex;
    gap: 2rem;
  }

  .main-panel {
    flex: 3;
  }

  .diag-panel {
    flex: 2;
  }
</style>

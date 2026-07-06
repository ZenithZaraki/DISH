<script lang="ts">
  import { runCommand } from '$lib/api';
  import { onMount, tick } from 'svelte';
  import { componentMap } from '$stores/componentMap';

  export let controls: Record<string, any[]> = {};

  let commandResults: Record<string, any> = {};
  let loadedComponents: Record<string, any> = {};

  async function loadComponent(type: string) {
    if (loadedComponents[type]) return loadedComponents[type];

    const entry = componentMap[type];
    if (!entry?.path) {
      console.warn(`⚠ Unknown component type: ${type}`);
      return null;
    }

    try {
      const mod = await import(/* @vite-ignore */ entry.path);
      loadedComponents[type] = mod.default;
      return mod.default;
    } catch (err) {
      console.error(`❌ Failed to import component "${type}":`, err);
      return null;
    }
  }

  async function handleCommand(control, extraPayload = {}) {
    const routingKey = control?.routing_key || control?.routingKey;

    if (!routingKey || typeof routingKey !== 'string') {
      console.warn('⚠️ Invalid routing key on control:', control);
      return;
    }

    const payload = {
      timestamp: new Date().toISOString(),
      ...extraPayload
    };

    try {
      const result = await runCommand({ command: routingKey, value: payload });

      const output = result?.status === 'executed'
        ? result.result
        : { error: result?.status || 'Unknown backend error' };

      commandResults = {
        ...commandResults,
        [routingKey]: output
      };

      await tick();
    } catch (err) {
      commandResults = {
        ...commandResults,
        [routingKey]: { error: err.message || 'Network or execution failure' }
      };
    }
  }

  function formatOutput(data: any): string {
    if (!data || typeof data !== 'object') return 'No data.';
    const spacer = (depth: number) => '&nbsp;'.repeat(depth * 4);

    const render = (obj: any, depth = 0): string[] =>
      Object.entries(obj).flatMap(([key, val]) =>
        typeof val === 'object' && val !== null
          ? [`${spacer(depth)}<strong>${key}:</strong><br>`, ...render(val, depth + 1)]
          : [`${spacer(depth)}<strong>${key}:</strong> ${val}<br>`]
      );

    return render(data).join('\n');
  }

  // Preload ReadOnly component
  onMount(async () => {
    await loadComponent('readonly');

    console.groupCollapsed('%c📋 [MANIFEST LOADED]', 'color: violet; font-weight: bold;');
    if (!controls || Object.keys(controls).length === 0) {
      console.warn('⚠️ No controls found in manifest!');
    } else {
      console.log('🎛 Control Groups:', Object.keys(controls));
      console.log('📦 Full Controls:', controls);
    }
    console.groupEnd();
  });
</script>

<div class="diag-ui">
  {#if Object.keys(controls).length > 0}
    {#each Object.entries(controls) as [groupName, groupControls]}
      <div class="diag-group">
        <h3>{groupName}</h3>

        {#each groupControls as control (control.routing_key)}
          <div class="form-entry">
            {#await loadComponent(control.type) then Component}
              {#if Component}
                <svelte:component
                  this={Component}
                  control={control}
                  result={commandResults[control.routing_key]?.[control.result_key] ?? commandResults[control.routing_key]}
                  on:trigger={(e) => handleCommand(control, e.detail || {})}
                />

                {#if control.type === 'button' && commandResults[control.routing_key]}
                  <svelte:component
                    this={loadedComponents['readonly']}
                    control={control}
                    result={commandResults[control.routing_key]}
                  />
                {/if}
              {:else}
                <div class="unknown-control">
                  <strong>⚠ Unknown component type:</strong> {control.type}
                </div>
              {/if}
            {:catch error}
              <div class="unknown-control">
                <strong>❌ Component load failed:</strong> {error.message}</div>
            {/await}
          </div>
        {/each}
      </div>
    {/each}
  {:else}
    <div class="no-controls">
      <em>No diagnostics available.</em>
    </div>
  {/if}
</div>
<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Exo+2:wght@800;900&family=Oxanium:wght@700;800&display=swap" rel="stylesheet">
<style>
  @import url('https://fonts.cdnfonts.com/css/ocr-a-extended');
  .diag-ui {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    height: 100%;
    max-height: 100vh;
    padding-left: .15rem;
    padding-right: .15rem;
    padding-bottom: .5rem;
    margin-left: 0%;
    margin-right: 0%;
    color: cyan;
    scrollbar-width: thin;
    scrollbar-color: #0ff transparent;
  }

  .diag-ui::-webkit-scrollbar {
    width: 6px;
  }

  .diag-ui::-webkit-scrollbar-thumb {
    background-color: #0ff;
    border-radius: 3px;
  }

  .diag-ui::-webkit-scrollbar-track {
    background-color: transparent;
  }

  .diag-group {
    margin-right: 0%;
    margin-left: 0%;
    padding-left: 0%;
    padding-right: 0%;
  }

  h3 {
    font-family: 'Audiowide', sans-serif;
    font-size: 1.5rem;
    margin-top: 0.75rem;
    margin-bottom: 0.5rem;
    color: #0ff;
  }

  .form-entry {
    margin-bottom: 1rem; /* spacing between stacked elements */
    margin-right: 0%;
    margin-left: 0%;
    display: flex;
    flex-direction: column;
    align-items: center; /* or left/right if you want tighter control */
  }

  .no-controls {
    font-family: sans-serif;
    font-size: 12.5px;
    text-align: center;
    font-style: italic;
    color: #888;
    margin-top: 2rem;
  }
</style>

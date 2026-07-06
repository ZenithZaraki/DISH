<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { componentMap } from '$stores/componentMap';
  import { runCommand } from '$lib/api';

  export let controls: any[] = [];

  let loadedComponents: Record<string, any> = {};
  let commandResults: Record<string, any> = {};
  let dynamicDropdownValues: Record<string, string[]> = {};
  let selectedValues: Record<string, string> = {};

  const zoneMap = {
    dropdown: 'left',
    filebrowser: 'left',
    toggle: 'left',
    textinput: 'left',
    readonly: 'center',
    structuredoutput: 'center',
    button: 'right'
  };

  function classifyControls(section) {
    const zones = { left: [], center: [], right: [] };
    for (const control of section.controls) {
      const zone = control.zone || zoneMap[control.type] || 'center';
      zones[zone].push(control);
    }
    return zones;
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
      console.error(`❌ Component load failed for ${type}:`, err);
      return null;
    }
  }

  function handleDropdownChange(routingKey: string, value: string) {
    selectedValues[routingKey] = value;
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
</script>

<div class="main-panel-ui">
  {#each controls as section (section.group)}
    <div class="group">
      {#if section.group}
        <h3>{section.group}</h3>
      {/if}

      {#key section}
        {#await Promise.resolve(classifyControls(section)) then zones}
          <div class="panel-zones">

            <!-- LEFT ZONE -->
            <div class="zone left">
              {#each zones.left as control (control.routing_key)}
                <div class="control-block">
                  {#await loadComponent(control.type) then Component}
                    {#if Component}
                      <svelte:component
                        this={Component}
                        control={control}
                        value={selectedValues[control.routing_key]}
                        options={dynamicDropdownValues[control.routing_key] || control.values}
                        resultOutput={commandResults[control.routing_key]?.logs?.join('\n') || commandResults[control.routing_key]?.message || ''}
                          on:trigger={async (e) => {
                            const routingKey = e.detail.command || control.routing_key;
                            const payload = e.detail.value || {};

                            commandResults[routingKey] = { logs: ["⏳ Submitting request..."] };
                            await tick();

                            try {
                              const result = await runCommand({ command: routingKey, value: payload });
                              commandResults[routingKey] = result.logs
                              ? { logs: result.logs }
                              : { message: result.message || JSON.stringify(result, null, 2) };
                            } catch (err) {
                              commandResults[routingKey] = { message: `❌ Error: ${err.message || 'Failed to run'}` };
                            }

                            await tick();
                          }}
                      />
                    {/if}
                  {/await}
                </div>
              {/each}
            </div>

            <!-- CENTER ZONE -->
            <div class="zone center">
              {#each zones.center as control (control.routing_key)}
                <div class="control-block">
                  {#await loadComponent(control.type) then Component}
                    {#if Component}
                      <svelte:component
                        this={Component}
                        control={control}
                        result={commandResults[control.routing_key]}
                      />
                    {/if}
                  {/await}
                </div>
              {/each}
            </div>

            <!-- RIGHT ZONE -->
            <div class="zone right">
              {#each zones.right as control (control.routing_key)}
                <div class="control-block">
                  {#await loadComponent(control.type) then Component}
                    {#if Component}
                      <svelte:component
                        this={Component}
                        control={control}
                        result={commandResults[control.routing_key]}
                        on:trigger={(e) => {
                          const payload = e.detail?.value || {};
                          handleCommand(control, payload);}}
                      />

                      {#if control.type === 'button' && commandResults[control.routing_key]}
                        {#await loadComponent('readonly') then ReadOnly}
                          {#if ReadOnly}
                            <svelte:component
                              this={ReadOnly}
                              control={control}
                              result={commandResults[control.routing_key]}
                            />
                          {/if}
                        {/await}
                      {/if}
                    {/if}
                  {/await}
                </div>
              {/each}
            </div>

          </div> 
        {/await}
      {/key}
    </div>
  {/each}
</div>
<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Exo+2:wght@800;900&family=Oxanium:wght@700;800&display=swap" rel="stylesheet">
<style>
@import url('https://fonts.cdnfonts.com/css/ocr-a-extended');
.main-panel-ui {
  height: auto !important;
  min-height: 0 !important;
  flex: 1;
  overflow-y: auto;
  padding-bottom: 0 !important;
  margin-bottom: 0 !important;
  color: cyan;
  background: #111;
  scrollbar-width: thin;
  scrollbar-color: rgb(25, 55, 55) transparent;
}

.group {
  margin-bottom: 0rem;
}

h3 {
  font-family: 'Audiowide', sans-serif;
  font-size: 1rem;
  margin-top: 0rem;
  margin-bottom: .1rem;
  text-align: center;
}

.panel-zones {
  display: flex;
  justify-content: stretch;  /* Fill full width */
  gap: 0;                    /* Optional, adjust as needed */
  padding: 0;
  width: 100%;
  min-height: auto !important;
  height: auto !important;
}

.zone.left,
.zone.right {
  width: 250px;             /* Fixed width */
  flex-shrink: 0;           /* Don't shrink */
  transition: width 0.3s ease;
}

.zone.left:empty,
.zone.right:empty {
  width: 0 !important;      /* Collapse completely */
  overflow: hidden;
  padding: 0;
  margin: 0;
}

.zone.center {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  margin: 0;
  padding: 0;
}

.group:last-child {
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}

.control-block {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.control-block select,
.control-block button {
  padding: 0.5rem 1rem;
  font-family: 'OCR A Extended', monospace;
  background: #000;
  border: 1px solid #0ff;
  border-radius: 6px;
  color: #ccc;
  transition: all 0.2s ease;
}

.control-block select:hover,
.control-block button:hover {
  color: cyan;
  box-shadow: 0 0 8px cyan;
}

body,
html {
  height: 100%;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
}

#app {
  flex: 1;
  display: flex;
  flex-direction: column;
}

footer,
.footer {
  flex-shrink: 0;
  margin: 0;
  padding: 2px 0 1px 0;
}
</style>
<script lang="ts">
  import { writable } from 'svelte/store';
  export let controls: Record<string, Record<string, any[]>> = {}; // zone -> group -> controls[]

  let state = writable({});

  function updateControl(name: string, value: any) {
    state.update(current => ({ ...current, [name]: value }));
    console.log(`[State] ${name} =`, value);
  }
</script>

<div class="module-ui">
  {#each Object.entries(controls) as [zone, groups]}
    <div class="zone-block">
      <h2>{zone.toUpperCase()}</h2>

      {#each Object.entries(groups) as [group, items]}
        <div class="group-block">
          <h3>{group}</h3>

          {#each items as control}
            <div class="form-row">
              {#if control.type === 'button'}
                <button on:click={() => console.log(`Clicked: ${control.text}`)}>
                  {control.text}
                </button>

              {:else if control.type === 'dropdown'}
                <label>
                  {control.name}
                  <select on:change={(e) => updateControl(control.name, e.target.value)}>
                    {#each control.values as value}
                      <option value={value}>{value}</option>
                    {/each}
                  </select>
                </label>

              {:else if control.type === 'file_browser'}
                <label>
                  {control.label || 'Select file:'}
                  <input
                    type="file"
                    multiple
                    accept={control.filetypes?.join(',') || '*/*'}
                    data-path={control.path}
                    on:change={(e) => updateControl(control.path, e.target.files)}
                  />
                </label>

              {:else if control.type === 'read_only'}
                <div class="readonly-block">
                  <em>{control.style}</em>
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .module-ui {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    padding: 1.5rem;
    color: cyan;
    background-color: #111;
    max-height: calc(100vh - 80px);
    overflow-y: auto;
  }

  .zone-block {
    border: 1px solid #044;
    padding: 1rem;
    border-radius: 8px;
    background-color: #1a1a1a;
  }

  h2 {
    font-size: 1.4rem;
    color: #00ffff;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #0ff;
  }

  h3 {
    font-size: 1.2rem;
    color: #0ff;
    margin-bottom: 0.3rem;
    text-shadow: 0 0 3px cyan;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-weight: bold;
  }

  select,
  input[type="file"],
  button {
    padding: 0.5rem;
    border: 1px solid #0ff;
    border-radius: 6px;
    background-color: #000;
    color: cyan;
    font-size: 1rem;
  }

  .readonly-block {
    border: 1px dashed #0ff;
    padding: 0.75rem;
    font-style: italic;
    opacity: 0.85;
    color: #ccc;
    background-color: #222;
  }
</style>

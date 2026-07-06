// Checkbox.svelte
<script>
  export let control;
  let isChecked = false;

  const handleChange = async () => {
    isChecked = !isChecked;
    await fetch('/run-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: control.routing_key,
        value: { checked: isChecked }
      })
    });
  };
</script>

<label>
  <input type="checkbox" bind:checked on:change={handleChange} />
  {control.label || control.name || 'Checkbox'}
</label>
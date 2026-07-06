<script>
  import { userState } from "./lib/userState";
  import Sidebar from './components/Sidebar.svelte';
  import EULADialog from "./components/EULADialog.svelte";
  import SwitchPanel from './components/SwitchPanel.svelte';
  import ScuzballOverlay from './components/ScuzballOverlay.svelte';
  import MainPanelRenderer from './components/MainPanelRenderer.svelte';
  import DiagPanelRenderer from './components/DiagPanelRenderer.svelte';
  import {
  fetchModuleManifest,
  fetchModuleRegistry   // ✅ ADD THIS LINE
} from '$lib/api.js';
  import { onMount } from 'svelte';
  import {
    selectedDiagControls,
    selectedModuleId,
    selectedModuleZones,
    selectedModule
  } from '$stores/modules';

  let accepted = userState.acceptedEULA;
  let sidebarOpen = true;
  let diagOpen = true;
  let registry = {}; // ✅ declare registry
  let groupedDiagControls = {};
  let groupedMainControls = [];
  let manifest;
  onMount(async () => {
  registry = await fetchModuleRegistry(); // ✅ use correct function
});

  

  $: if ($selectedModuleId) {
  fetchModuleManifest($selectedModuleId)
    .then((result) => {
      manifest = result;
    })
    .catch((err) => {
      console.error(`[Manifest Load] Failed for ${$selectedModuleId}:`, err);
    });
}

  $: console.log('📦 selectedModule:', $selectedModule);
  $: console.log('selectedDiagControls:', $selectedDiagControls);

  // Grouping logic
  $: {
    const main = $selectedModuleZones?.main || {};
    groupedMainControls = Object.entries(main).map(([group, controls]) => ({
      group,
      controls
    }));
  }

  $: groupedDiagControls = $selectedDiagControls;

  $: {
    console.log('[GROUPED DIAG CONTROLS]', groupedDiagControls);
  }

  onMount(async () => {
    registry = await fetchModuleRegistry(); // ✅ use correct function
  });

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function toggleDiag() {
    diagOpen = !diagOpen;
  }
</script>
{#if !userState.acceptedEULA}
  <EULADialog />
{:else}
  <header class="dish-header">
    <div class="header-buttons">
      <button class="hamburger-button" on:click={toggleSidebar}>☰</button>
      <button class="wrench-button" on:click={toggleDiag}>⚙️</button>
    </div>
    <div class="header-body">
      <h1>SAF DISH</h1>
      <p class="subtext">SkyTeam Aerospace Foundation Unified Digital Interface</p>
      <p class="tagline">
        "Because managing unstable sentient software should look good while it's melting your core..."
      </p>
    </div>
  </header>

  <div class="content">
    <div class={`sidebar ${sidebarOpen ? '' : 'hidden'}`}>
      <Sidebar {registry} selectedModule={$selectedModuleId} />
    </div>

    <div class="mainzone">
      {#if $selectedModuleId === 'switchboard'}
        <SwitchPanel {registry} />
      {:else}
        <MainPanelRenderer controls={groupedMainControls} />
      {/if}
    </div>

    <div class={`diag ${diagOpen ? '' : 'hidden'}`}>
      <DiagPanelRenderer controls={$selectedDiagControls} />
    </div>
  </div>

  <ScuzballOverlay />

  <footer class="dish-footer">
    <span>Digital Intelligence Stack Host —</span>
    <span class="version">vBeta 0.4.6 — "The AI knows. You should’ve used dark mode sooner".</span>
  </footer>
{/if}
<link href="https://fonts.googleapis.com/css2?family=Audiowide&family=Exo+2:wght@800;900&family=Oxanium:wght@700;800&display=swap" rel="stylesheet">
<style>

  :root{
    --cut: 10px;           /* bevel depth */
    --bw: 2px;             /* border width */
    --c:  #00ffff;         /* border/glow color */
  }

  .container {
    display: auto;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    margin: 0;
    overflow: hidden; /* ✅ no vertical scrollbars */
    background-color: #2d2d2d;
  }

  .content {
    display: flex;
    flex: 1 1 auto;
    overflow: hidden; /* ✅ disables scroll inside main content */
    height: calc(93.5vh - 90px); /* ✅ accounts for header+footer height */
    z-index: 2; /* Bring the panels in front */
  }

  .sidebar {
    width: 300px;
    flex-shrink: 0;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(6px) saturate(140%);
    border-right: 1px solid rgba(0, 255, 255, 0.8);
    border-top-right-radius: 14px;
    border-bottom-right-radius: 14px;
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    box-shadow:
      0 0 20px rgba(0, 255, 255, 0.15),   /* outer soft aura */
      inset 0 0 25px rgba(0, 255, 255, 0.05), /* inner cyan fade */
      0 8px 25px rgba(0, 0, 0, 0.6);       /* floating depth shadow */
    transition: all 0.4s ease;
    transform: translateZ(0); /* keeps GPU rendering clean */
    color: cyan;
    border-right: 1px solid #0ff;
    transition: width 0.3s ease;
    overflow: hidden;
    z-index: 1; /* Bring the panels in front */
  }

  .sidebar.hidden {
    width: 0;
    overflow: hidden;
    border-right: none;
    padding: 0;
  }

  .diag {
    width: 320px;
    flex-shrink: 0;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(6px) saturate(140%);
    border-left: 1px solid rgba(0, 255, 255, 0.8);
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    box-shadow:
      0 0 20px rgba(0, 255, 255, 0.15),   /* outer soft aura */
      inset 0 0 25px rgba(0, 255, 255, 0.05), /* inner cyan fade */
      0 8px 25px rgba(0, 0, 0, 0.6);       /* floating depth shadow */
    transition: all 0.4s ease;
    transform: translateZ(0); /* keeps GPU rendering clean */
    color: cyan;
    border-left: 1px solid #0ff;
    transition: width 0.3s ease;
    overflow: hidden;
    z-index: 1; /* Bring the panels in front */
  }

  .diag.hidden {
    width: 0;
    overflow: hidden;
    border-left: none;
    padding: 0;
  }

  .mainzone {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    margin: 0;
    padding: 1rem;
    background-color: #111;
    color: white;
    overflow-y: auto; /* ✅ allows internal scroll if content grows */
    overflow-x: hidden;
  }

  .sidebar:hover,
  .diag:hover {
    background: rgba(0, 0, 0, 0.6);
    box-shadow:
      0 0 30px rgba(0, 255, 255, 0.25),
      inset 0 0 30px rgba(0, 255, 255, 0.1),
      0 12px 35px rgba(0, 0, 0, 0.7);
    transform: translateY(-2px);
  }

  html, body {
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden; /* ✅ stops body scrollbars */
    max-width: 100vw;
  }

  * {
    box-sizing: border-box;
  }

  body > * {
    max-width: 100vw;
    overflow-x: hidden;
  }

  .dish-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 6px 10px;
    background-color: #111;
    border-bottom: 1px solid #00ffff;
    position: relative;
    z-index: 0; /* Push it back one layer */
    text-align: center;
  }

  .header-body {
    width: 100%;
    position: relative;
  }

  .dish-header h1 {
    font-family: 'Audiowide', sans-serif;
    font-size: 2rem;
    font-style: italic;
    color: #00ffff;
    margin: 0;
  }

  .dish-header .subtext {
    font-family: 'Audiowide', sans-serif; 
    font-size: 0.85rem;
    font-style: italic;
    color: #00ffff;
    margin: 0;
  }

  .dish-header .tagline {
    font-family: sans-serif;
    font-size: 12.5px;
    color: #888;
    font-style: italic;
    margin-top: 2px;
  }

  .header-buttons {
    position: absolute;
    top: 6px;
    left: 10px;
    display: flex;
    gap: 8px;
    z-index: 2;
  }

  .hamburger-button,
  .wrench-button {
    background-color: #222;
    border: 1px solid #0ff;
    border-radius: 6px;
    color: cyan;
    outline: none;
    box-shadow: none;
    padding: 0.3rem 0.5rem;
    font-size: 1rem;
    cursor: pointer;
    transition: 
      box-shadow 0.3s ease,
      color 0.3s ease,
      border-color 0.3s ease;
  }

  .hamburger-button:hover,
  .wrench-button:hover {
    box-shadow: 0 0 8px #00ffff, 0 0 16px #00ffff;
    transform: scale(1.1);
  }

  @keyframes slideLeft {
    from { transform: translateX(50px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }

  .dish-header {
    animation: slideLeft 0.5s ease-out;
  }

  .dish-footer {
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: 'Audiowide', sans-serif;
    font-size: 12px;
    color: #00ffff;
    background-color: #111;
    border-top: 1px solid #00ffff;
    height: 28px;
    padding: 0 10px;
    overflow: hidden;
    white-space: nowrap;
  }

  .version {
    margin-left: 0.5em;
    font-family: sans-serif;
    font-size: 12.5px;
    font-style: italic;
    color: #888;
  }

</style>

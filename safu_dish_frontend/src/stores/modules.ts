import { writable, derived } from 'svelte/store';
import { fetchModuleManifest, fetchModuleRegistry } from '$lib/api.js';

export const modules = writable([]);
export const selectedModuleId = writable('switchboard'); // Hardcoded fallback

// Async init block
(async () => {
  try {
    const registry = await fetchModuleRegistry();
    const manifest = {};

    for (const moduleId of Object.keys(registry)) {
      try {
        manifest[moduleId] = await fetchModuleManifest(moduleId);
      } catch (err) {
        console.warn(`[Module Init] Skipping ${moduleId} — no manifest loaded.`);
      }
    }

    const combined = Object.entries(manifest).map(([moduleId, zones]) => {
      const reg = registry[moduleId] || {};

      const controls = {}; // funcName -> { group, zone, controls }

      for (const [zone, funcs] of Object.entries(zones)) {
        for (const [funcName, block] of Object.entries(funcs)) {
          controls[funcName] = {
            ...block,
            zone
          };
        }
      }

      return {
        id: moduleId,
        display_name: reg.display_name || moduleId,
        enabled: reg.enabled ?? true,
        locked: reg.locked ?? false,
        controls
      };
    });

    modules.set(combined);

    // Ensure selected module is valid, fallback to first or switchboard
    selectedModuleId.update(current => {
      const found = combined.find(mod => mod.id === current);
      return found ? current : (combined[0]?.id || 'switchboard');
    });
  } catch (err) {
    console.error('❌ Failed to load module manifest or registry:', err);
  }
})();

// Track current module
export const selectedModule = derived(
  [modules, selectedModuleId],
  ([$modules, $selectedModuleId]) =>
    $modules.find(mod => mod.id === $selectedModuleId)
);

// Track UI controls for current module (grouped by zone, then group)
export const selectedModuleControls = derived(
  selectedModule,
  $mod => {
    if (!$mod || !$mod.controls) return {};

    const zones = {};

    for (const [funcName, funcData] of Object.entries($mod.controls)) {
      const zone = funcData.zone || 'main';
      const group = funcData.group || 'Ungrouped';

      if (!zones[zone]) zones[zone] = {};
      if (!zones[zone][group]) zones[zone][group] = [];

      zones[zone][group].push(...(funcData.controls || []));
    }

    return zones;
  }
);

// ✅ NOW EXPORT ZONE DERIVED STORES (after selectedModuleControls exists)
export const selectedSidebarControls = derived(selectedModuleControls, $c => $c.sidebar || {});
export const selectedMainControls = derived(selectedModuleControls, $c => $c.main || {});
export const selectedDiagControls = derived(selectedModuleControls, $c => $c.diag || {});
export const selectedModuleZones = selectedModuleControls;

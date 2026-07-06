const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

// ✅ GET: Single module manifest
export async function fetchModuleManifest(moduleName) {
  try {
    const res = await fetch(`${API_BASE}/api/manifest/${moduleName}`);
    if (!res.ok) throw new Error(`Failed to load manifest for ${moduleName}`);
    return await res.json();
  } catch (err) {
    console.error(`[DISH API] Manifest fetch error for ${moduleName}:`, err);
    throw err;
  }
}

// ✅ GET: All module manifests (newly added)
export async function fetchAllModuleManifests() {
  try {
    const res = await fetch(`${API_BASE}/api/interface`);
    if (!res.ok) throw new Error('Failed to fetch full module manifest');
    return await res.json();
  } catch (err) {
    console.error('[DISH API] fetchAllModuleManifests failed:', err);
    throw err;
  }
}

// ✅ GET: Live module registry
export async function fetchModuleRegistry() {
  try {
    const res = await fetch(`${API_BASE}/api/modules/registry`);
    if (!res.ok) throw new Error('Registry fetch failed');
    return await res.json();
  } catch (err) {
    console.warn('[DISH API] Using fallback registry.json:', err.message);
    const fallback = await fetch('/registry.json');
    return await fallback.json();
  }
}

// ✅ POST: Generic command runner
export async function runCommand(requestBody) {
  if (
    typeof requestBody !== 'object' ||
    !requestBody.command ||
    typeof requestBody.command !== 'string' ||
    typeof requestBody.value !== 'object'
  ) {
    console.error('[DISH API] Invalid runCommand payload:', requestBody);
    throw new Error('runCommand payload must be an object with "command" and "value"');
  }

  try {
    const res = await fetch(`${API_BASE}/run-command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    if (!res.ok) {
      const errText = await res.text();
      console.error('[DISH API] Server Error:', errText);
      throw new Error(errText);
    }

    return await res.json();
  } catch (err) {
    console.error(`[DISH API] Command failed:`, err);
    throw err;
  }
}

// ✅ POST: File uploader
export async function uploadFiles(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file); // ✅ key must match FastAPI param: `files`
  }

  const res = await fetch(`${API_BASE}/uploads`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

// ✅ Alias to match component import
export const uploadFile = uploadFiles;

// ✅ POST: Streaming command runner (for chat)
export async function runStreamCommand(requestBody, onToken) {
  if (
    typeof requestBody !== 'object' ||
    !requestBody.message
  ) {
    console.error('[DISH API] Invalid runStreamCommand payload:', requestBody);
    throw new Error('runStreamCommand payload must include { message }');
  }

  const res = await fetch(`${API_BASE}/api/modules/NOVA/respond?stream=true`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Streaming request failed: ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });

    // Split on newlines (tokens can be partial)
    chunk.split(/\r?\n/).forEach(token => {
      if (token.trim()) {
        onToken(token);
      }
    });
  }
}

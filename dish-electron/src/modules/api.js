/**
 * @typedef {never} UNSPECIFIED_JSON
 */

/**
 * @typedef {{type:string,attrs:Record<string,string>,id:string?,routing_key:string,payload:Record<string,string>}} UIComponent
 * @typedef {{zone:string,name:string,components:UIComponent[]}} UIGroup
 * @typedef {UIGroup[]} UIManifest
 * @typedef {Record<string,{name:string,display_name:string}>} ModuleRegistry
 */

export const API_BASE = 'http://127.0.0.1:8000';

const CACHED_MODULE_DATA = {
    REGISTRY: null,
    MANIFESTS: {},
};

export function invalidateModuleCache() {
    CACHED_MODULE_DATA.REGISTRY = null;
    CACHED_MODULE_DATA.MANIFESTS = {};
}

/**
 * fetches the module registry and all module manifests
 * @returns {Promise<{registry:ModuleRegistry,manifest:Record<string,UIManifest>}>}
 */
export async function fetchModules() {
    const reg = await fetchModuleRegistry();
    const man = {};
    await Promise.allSettled(Object.keys(reg).map(id => new Promise(async r=>{man[id]=await fetchModuleManifest(id);r();})));
    // for (const id in reg) {
    //     man[id] = await fetchModuleManifest(id);
    // }
    return {registry:reg,manifest:man};
}
fetchModules(); // starts a background fetch of all module data that will then be cached

/**
 * @param {string} moduleName
 * @returns {Promise<UIManifest>}
 */
export async function fetchModuleManifest(moduleName) {
    if (moduleName in CACHED_MODULE_DATA.MANIFESTS) {
        return CACHED_MODULE_DATA.MANIFESTS[moduleName];
    }
    try {
        const res = await fetch(`${API_BASE}/api/manifest/${moduleName}`);
        if (!res.ok) throw new Error(`Failed to load manifest for ${moduleName}`);
        const result = await res.json();
        CACHED_MODULE_DATA.MANIFESTS[moduleName] = result;
        return result;
    } catch (err) {
        console.error(`[DISH API] Manifest fetch error for ${moduleName}:`, err);
        throw err;
    }
}

// commented because there is no api route "/api/interface"
// export async function fetchAllModuleManifests() {
//     try {
//         const res = await fetch(`${API_BASE}/api/interface`);
//         if (!res.ok) throw new Error('Failed to fetch full module manifest');
//         return await res.json();
//     } catch (err) {
//         console.error('[DISH API] fetchAllModuleManifests failed:', err);
//         throw err;
//     }
// }

/**
 * @returns {Promise<ModuleRegistry>}
 */
export async function fetchModuleRegistry() {
    if (CACHED_MODULE_DATA.REGISTRY) {
        return CACHED_MODULE_DATA.REGISTRY;
    }
    try {
        const res = await fetch(`${API_BASE}/api/modules/registry`);
        if (!res.ok) throw new Error('Registry fetch failed');
        const result = await res.json();
        CACHED_MODULE_DATA.REGISTRY = result;
        return result;
    } catch (err) {
        console.warn('[DISH API] Using fallback registry.json:', err.message);
        const fallback = await fetch('/registry.json');
        return await fallback.json();
    }
}

/**
 * runs a command
 * @param {{command:string,value:object}} requestBody
 * @returns {Record<string,any>}
 */
export async function runCommand(requestBody) {
    if (
        typeof requestBody !== 'object' ||
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

/**
 * uploads a file to the backend
 * @param {string[]} files
 * @returns {Record<string,any>}
 */
export async function uploadFiles(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    const res = await fetch(`${API_BASE}/uploads`, {
        method: 'POST',
        body: formData,
    });

    if (!res.ok) throw new Error(await res.text());
    return await res.json();
}

/**
 * runs a command with a streamed result
 * @param {{message:string}&object} requestBody
 * @param {(token:string)=>void} onToken
 */
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

/**
 * @param {UIManifest} manifest
 * @param {string} zone
 * @param {(name:string,children:HTMLElement[])=>HTMLElement} makeGroup
 * @returns {HTMLElement[]}
 */
export function renderModuleArea(manifest, zone, makeGroup) {
    return manifest.filter(v => v.zone === zone).map(group => {
        return makeGroup(group.name, group.components.map(comp => {
            const root = (()=>{const l = comp.type.split("/");const f =l.slice(0,l.length-1).join("/");if(f.length)return`components/${f}`;return f;})();
            const name = comp.type.split("/").pop();
            const inc = document.createElement("x-include");
            inc.setAttribute("tagname", `x-${name}`);
            if (root) inc.setAttribute("root", root);
            inc.setAttribute("name", name);
            const pass = {
                ...comp.attrs??{}
            };
            if (comp.id)pass.id=comp.id;
            if (comp.routing_key&&comp.routing_key!=="!")pass["routing-key"]=comp.routing_key;
            if (comp.payload)pass.payload=JSON.stringify(comp.payload);
            inc.setAttribute("pass", JSON.stringify(pass));
            return inc;
        }));
    });
}

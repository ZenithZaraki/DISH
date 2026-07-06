// buildComponentMap.js

const fs = require('fs');
const path = require('path');

// === Configurable Paths ===
const COMPONENT_DIR = path.resolve(__dirname, '..', 'lib', 'components');
const TS_OUTPUT_PATH = path.resolve(__dirname, '..', 'stores', 'componentMap.ts');
const JSON_OUTPUT_PATH = path.join(__dirname, '..', '..', '..', 'safu_dish_backend', 'app', 'config', 'component_manifest.json');

// === Utility: Convert PascalCase to kebab-case for HTML tags (optional)
const toKebab = str =>
  str.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();

// === Step 1: Scan Components Folder ===
const componentFiles = fs.readdirSync(COMPONENT_DIR).filter(file => file.endsWith('.svelte'));

const manifest = {};

componentFiles.forEach(file => {
  const baseName = path.basename(file, '.svelte');

  manifest[baseName] = {
    type: baseName.toLowerCase(),       // Optional normalization
    tag: toKebab(baseName),             // Useful for dynamic HTML injection
    file: file,                         // Raw filename
    path: `/src/lib/components/${file}`,        // Aliased import path used in Svelte
    props: []                           // Placeholder — expandable later
  };
});

// === Step 2: Write TypeScript for Frontend ===
const tsContent = `// AUTO-GENERATED FILE — DO NOT EDIT
export const componentMap = ${JSON.stringify(manifest, null, 2)};
`;
fs.writeFileSync(TS_OUTPUT_PATH, tsContent);
console.log(`✅ TypeScript map written: ${TS_OUTPUT_PATH}`);

// === Step 3: Write JSON for Backend ===
fs.writeFileSync(JSON_OUTPUT_PATH, JSON.stringify(manifest, null, 2));
console.log(`✅ Backend manifest JSON written: ${JSON_OUTPUT_PATH}`);

// src/lib/stores/instructionStore.js
import { writable } from 'svelte/store';

// Shared instruction text — dynamically available across modules
export const instructionText = writable('');

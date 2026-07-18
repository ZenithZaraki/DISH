import * as fs from 'fs';
import * as path from 'path';
import { lex } from './dish-electron/src/modules/pixl.mjs';
export { lex } from './dish-electron/src/modules/pixl.mjs';

export const test_input = fs.readFileSync(path.join(import.meta.dirname, "examples", "simpleAPM", "ui", "logic.pixl"), "ascii");

export const test_output = lex(test_input);

// console.log(test_input);
console.log(test_output);

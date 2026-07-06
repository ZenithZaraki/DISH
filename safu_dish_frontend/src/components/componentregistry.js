// ComponentRegistry.js

import Button from './components/ui/Button.svelte';
import Toggle from './components/ui/Toggle.svelte';
import Dropdown from './components/ui/Dropdown.svelte';
import TextInput from './components/ui/TextInput.svelte';
import ReadOnly from './components/ui/ReadOnly.svelte';
import Checkbox from './components/ui/Checkbox.svelte';
import FileBrowser from './components/ui/FileBrowser.svelte';
import StructuredOutput from './components/ui/StructuredOutput.svelte';

export const componentRegistry = {
  button: Button,
  toggle: Toggle,
  dropdown: Dropdown,
  text_input: TextInput,
  read_only: ReadOnly,
  checkbox: Checkbox,
  file_browser: FileBrowser,
  structured_output: StructuredOutput
};

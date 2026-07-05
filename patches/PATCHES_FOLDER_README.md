# Patches

This folder is used for DISH CORE NOVA Edition patch files, update notes, and targeted replacement components.

The full DISH system package is distributed separately because the complete runtime archive is too large for direct GitHub hosting. This folder exists so small fixes and updates can be posted without requiring users to download the entire system again.

## Purpose

Use this folder to store:

- Patch notes
- Replacement scripts
- Updated frontend components
- Updated backend components
- Runtime fixes
- Parser fixes
- Configuration fixes
- Install instructions for specific updates

## Folder Use

Each patch should be placed in its own subfolder when possible.

Recommended structure:

```text
patches/
  README.md
  patch-name/
    README.md
    files/
```

Each patch subfolder should explain what the patch changes, which DISH version it applies to, and where the replacement files should be copied.

## Important Notes

Patches in this folder are meant for targeted updates only.

They are not a replacement for the full DISH system package.

Users should only apply patches that match their installed DISH version and the affected component.

## Version Scope

Unless stated otherwise, patches in this folder are intended for:

```text
DISH CORE NOVA Edition v1
Development Beta Release
```

## Full System Package

The full portable DISH package is hosted separately from GitHub.

Refer to the main project README for the current full-system download link and setup information.

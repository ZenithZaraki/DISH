# Test_APM Patch Notes

## Patch: Test_APM Runtime and Inference Fixes

**Target:** DISH CORE NOVA Edition v1  
**Component:** `Test_APM`  
**Patch type:** Targeted replacement files  
**Status:** Development beta patch

## Summary

This patch updates the `Test_APM` module files used for runtime execution, inference testing, and embedder support.

The patch includes updates for:

- `functions.py`
- `test_inference.py`

## Updated Files

```text
Test_APM/functions.py
Test_APM/test_inference.py
```

## Directory Location

The patched files belong in the `Test_APM` module directory.

Default DISH backend path:

```text
SAFU NOVA\safu_dish_backend\app\modules\Test_APM
```

Expected file locations:

```text
SAFU NOVA\safu_dish_backend\app\modules\Test_APM\functions.py
SAFU NOVA\safu_dish_backend\app\modules\Test_APM\test_inference.py
```

Users should open the DISH backend folder, then follow this path:

```text
safu_dish_backend
└── app
    └── modules
        └── Test_APM
            ├── functions.py
            └── test_inference.py
```

Replace the existing files in that directory with the patched versions.

## functions.py Update

### Change

Embedder runtime support has been enabled in `functions.py`.

### Purpose

This update allows the `Test_APM` module to support embedder runtime behavior during module execution and testing.

### Expected Result

After applying this update, `Test_APM` should be able to initialize and use the embedder runtime pathway as part of the module workflow.

### Notes

This update is intended for the development beta runtime and may be adjusted again as the embedder pipeline is refined.

## test_inference.py Update

### Change

The stop sequence handling issue has been fixed in `test_inference.py`.

### Purpose

The prior version could fail during generation because stop sequence logic was referenced without being properly active or defined.

### Expected Result

After applying this update, inference testing should no longer fail or stall due to missing stop sequence handling.

### Notes

This fix is intended to improve model output stability during local inference testing.

## Install Instructions

1. Close the DISH backend/runtime if it is currently running.
2. Navigate to the `Test_APM` module directory:

```text
SAFU NOVA\safu_dish_backend\app\modules\Test_APM
```

3. Replace the existing files with the patched versions:

```text
SAFU NOVA\safu_dish_backend\app\modules\Test_APM\functions.py
SAFU NOVA\safu_dish_backend\app\modules\Test_APM\test_inference.py
```

## Directory Location

The patched files belong in the `Test_APM` module directory.

Default DISH backend path:

```text
SAFU NOVA\safu_dish_backend\app\modules\Test_APM
```

Expected file locations:

```text
SAFU NOVA\safu_dish_backend\app\modules\Test_APM\functions.py
SAFU NOVA\safu_dish_backend\app\modules\Test_APM\test_inference.py
```

Users should open the DISH backend folder, then follow this path:

```text
safu_dish_backend
└── app
    └── modules
        └── Test_APM
            ├── functions.py
            └── test_inference.py
```

Replace the existing files in that directory with the patched versions.

4. Restart the DISH backend/runtime.
5. Run a basic inference test.
6. Confirm that output is generated normally.
7. Confirm that the embedder runtime pathway loads as expected.

## Version Scope

This patch is intended for:

```text
DISH CORE NOVA Edition v1
Development Beta Release
```

## Compatibility Notes

This patch is intended only for the `Test_APM` development module.

Do not apply these files to unrelated modules unless the file structure and runtime logic match the `Test_APM` module layout.

## Known Notes

DISH CORE NOVA Edition v1 is a development beta. Additional targeted patches may be released as module routing, runtime execution, parser behavior, and frontend integration are tested across different systems.

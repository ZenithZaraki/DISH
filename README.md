# DISH CORE NOVA Edition v1

**DISH CORE NOVA Edition v1** is a development beta release of the **Digital Intelligence Stack Host** core system.

This release is **not** the completed full DISH platform. It is the base core system prepared for testing, tinkering, expansion, and early development work. It includes the foundational NOVA Edition structure, a beta data parser, a DirectML-configured model runner, two APMs for testing and expansion, and two included local models.

DISH CORE NOVA Edition v1 is intended to provide a portable core environment for experimenting with DISH architecture before the full stack is finalized.

## Download

DISH CORE NOVA Edition v1 portable package:

https://1drv.ms/u/c/41b51cd7c37f4d07/IQC9EJHb6tgcQKdJthrUVlJbAccEB6GnEfdyRHEJ2t5EgX8

## Official DISH Information

Further information about DISH can be found on the official SkyTeam Aerospace Foundation DISH page:

https://www.skyteamaerospacefoundation.com/dish

## Release Status

| Field | Value |
| --- | --- |
| Release Type | Development Beta |
| System Type | Portable Core System |
| Version | v1 |
| Primary Runtime Path | DirectML |
| Status | Experimental / In Development |

This release is functional for testing and expansion, but it should not be treated as a final production release.

## What This Release Includes

DISH CORE NOVA Edition v1 includes:

- Base DISH core system
- NOVA Edition runtime structure
- Beta data parser
- Model runner
- DirectML runtime setup
- Two included APMs for tinkering and expansion
- Two included local models for testing and experimentation

The included APMs are experimental and are intended for early testing, modification, and development expansion.

## Included Models

This development beta includes the following models for local testing and experimentation:

- `e5-small-v2-onnx`
- `Phi-3.5-mini-instruct`

### e5-small-v2-onnx

The included `e5-small-v2-onnx` model is credited to the original `intfloat/e5-small-v2` model and the ONNX-compatible `Xenova/e5-small-v2` variant.

- Original model: https://huggingface.co/intfloat/e5-small-v2
- ONNX-compatible variant: https://huggingface.co/Xenova/e5-small-v2

The `intfloat/e5-small-v2` model is listed on Hugging Face as a sentence similarity model with ONNX support and an MIT license. The model card identifies the model as having 12 layers and an embedding size of 384.

The `Xenova/e5-small-v2` model card identifies it as a feature extraction model for Transformers.js and states that it is based on `intfloat/e5-small-v2` with ONNX weights for compatibility with Transformers.js.

### Phi-3.5-mini-instruct

`Phi-3.5-mini-instruct` is credited to Microsoft.

- Model card: https://huggingface.co/microsoft/Phi-3.5-mini-instruct

The Microsoft `Phi-3.5-mini-instruct` model card is hosted under Microsoft on Hugging Face and identifies the model as part of Microsoft’s Phi model family.

`Phi-3.5-mini-instruct` is included in this release as a local instruction model for experimentation with the DISH model runner.

## Model Attribution Notice

The included models are third-party components and are not authored by Zenith Zaraki or SkyTeam Aerospace Foundation.

DISH CORE NOVA Edition v1 includes these models only as bundled runtime and test components for local experimentation. Their original authors, repositories, model cards, and licenses remain authoritative.

Users are responsible for reviewing and following the terms, licenses, and usage guidance for each included model.

## What This Release Is Not

This release is not the completed full DISH system.

It is not a final production build, polished commercial release, complete public platform, or full implementation of the DISH system vision. It is the core foundation package for development and testing.

## Technology Stack and Third-Party Attributes

DISH CORE NOVA Edition v1 is built with or includes support for the following technologies:

- Svelte
- Node.js
- Electron
- Python
- FastAPI
- Microsoft DirectML
- Torch / PyTorch
- CUDA support pathway
- Local model execution tooling

### Svelte

Svelte is credited as the frontend framework used for DISH interface development.

Official site: https://svelte.dev/

### Node.js

Node.js is credited as the JavaScript runtime environment used by the system’s desktop and web tooling layer.

Official site: https://nodejs.org/en/about

### Electron

Electron is credited as the desktop application framework used to package web technologies into a local desktop application.

Official documentation: https://www.electronjs.org/docs/latest/

### Python

Python is credited as the backend and runtime language used for DISH service logic, parser behavior, and AI workflow support.

Official site: https://www.python.org/

### FastAPI

FastAPI is credited as the Python API framework used for backend service routing and local API behavior.

Official documentation: https://fastapi.tiangolo.com/

### Microsoft DirectML

Microsoft DirectML is credited as the primary configured hardware acceleration path for this beta model runner.

Official documentation: https://learn.microsoft.com/en-us/windows/ai/directml/dml

### Torch / PyTorch

Torch / PyTorch is credited as part of the machine learning framework pathway used for local model execution.

Official site: https://pytorch.org/

### CUDA

CUDA is credited as a future and/or supported acceleration pathway for NVIDIA GPU-based execution where applicable.

Official toolkit page: https://developer.nvidia.com/cuda-toolkit

## Runtime Focus

DirectML is the primary configured model execution path for this beta release.

CUDA is part of the broader technical direction, but this beta package is focused on validating the core system and DirectML-based model runner.

## SAF Framework Codex and Documentation

DISH is being developed alongside the SAF Framework and broader SAFU research ecosystem.

The **SAF Framework Codex** serves as the primary documentation and user manual for DISH. It is intended to explain the system’s concepts, structure, usage, development direction, terminology, and operational philosophy as DISH continues to evolve.

The Codex is currently under development and can be found here:

https://www.royalroad.com/fiction/138960/saf-framework-codex

Because DISH and the SAF Framework are still actively developing, the Codex should be treated as living documentation. Terminology, architecture notes, user guidance, and framework explanations may change as the system matures.

For further information about DISH, visit the official SkyTeam Aerospace Foundation DISH page:

https://www.skyteamaerospacefoundation.com/dish

## Core Purpose

DISH CORE NOVA Edition v1 exists to provide a local-first foundation for modular AI experimentation and DISH system expansion.

The core is intended for:

- Testing the base DISH structure
- Experimenting with local AI workflows
- Running early model execution tests
- Developing parser behavior
- Expanding APM modules
- Supporting SAF Framework-aligned research
- Validating portable deployment behavior

## Portability

This release is distributed as a portable package.

The folder structure should remain intact after extraction. Internal paths, runtime dependencies, parser components, model runner files, included models, and APM structures are expected to remain together.

Recommended extraction example:

```text
D:\DISH_CORE_NOVA_Edition_v1\
```

Avoid placing the system in protected Windows directories or paths with unusual characters. Do not move internal folders unless you understand the system structure and dependency paths.

## License

DISH CORE NOVA Edition v1 is governed by the DISH End-User License Agreement.

The EULA is provided separately in this repository.

Use, redistribution, modification, derivative work, and authorized access are subject to the terms defined in that EULA.

Third-party components, frameworks, runtimes, and included models remain governed by their own respective licenses.

## Development Notes

This beta release is meant to establish the base DISH CORE NOVA Edition system and provide a working foundation for future development.

Current development priorities include:

- Core stability
- DirectML model runner validation
- Beta parser refinement
- APM expansion
- Documentation growth
- SAF Framework alignment
- Runtime cleanup
- Future CUDA pathway support

## Disclaimer

This is an experimental development beta. It may contain incomplete features, undocumented behavior, rough edges, and unstable components.

It is intended for testing, tinkering, expansion, and early system validation.

Do not treat this as the final DISH system.

## Credits

DISH CORE NOVA Edition is developed by Zenith Zaraki as part of the broader SAFU / SAF Framework ecosystem.

Third-party models and technologies included or referenced in this release remain credited to their respective creators, maintainers, and organizations.

SAF Framework Codex:

https://www.royalroad.com/fiction/138960/saf-framework-codex

Official DISH page:

https://www.skyteamaerospacefoundation.com/dish

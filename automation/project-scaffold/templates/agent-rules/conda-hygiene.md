## 🐍 Python & Conda / Mamba Environment Management Protocol

Follow these mandatory practices whenever setting up, modifying, or exporting Python and Conda environments:

### 1. Declarative & Clean `environment.yml`
- **Never lock transitive system libraries**: Do not commit dirty exports containing low-level C runtimes (`ca-certificates`, `m2w64-*`, `vc14_runtime`, `ucrt`, `openssl`, `lib*`). Only declare top-level business and framework dependencies.
- **Never hardcode local paths (`prefix:`)**: All `environment.yml` deliverables must omit local system prefix paths to ensure full portability across developer machines.
- **Pin only semantic constraints**: Use `>=` or `~=` for library version bounds unless a specific bug requires pinning an exact minor patch.

### 2. High-Speed Tooling: Mamba Over Conda
- **Default to Mamba**: Always prioritize using `mamba` (via Miniforge or system PATH) rather than legacy `conda`. Mamba's C++ `libsolv` engine resolves environments in seconds rather than minutes.
- **Automated Tooling**: Use `python tools/env_tool.py doctor` for hardware/driver diagnosis and `python tools/env_tool.py setup` for automated environment bootstrap and daemon runner configuration.

### 3. Environment Isolation & Workspace Naming
- **Domain Prefixes for Global Environments**: When naming global conda environments (`-n`), use standardized domain prefixes (`ai-*`, `sec-*`, `ds-*`, `tool-*`, `paper-*`) to enable clean grouping and terminal tab-completion.
- **Project-Local Prefix Mode**: For dedicated repositories, prefer creating local workspace environments (`-p ./.conda`). VS Code / PyCharm will automatically discover the project interpreter without polluting global Conda registries.

### 4. GPU VRAM Safety Guardrails
- On machines equipped with consumer or laptop NVIDIA GPUs (<= 8GB VRAM), all PyTorch scripts must clamp memory allocation fraction (`torch.cuda.set_per_process_memory_fraction(0.65)`) to prevent display driver TDR resets and remote desktop disconnections.

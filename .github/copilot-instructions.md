
# Copilot Instructions

This file provides high-level instructions for Copilot and other AI assistants working in this repository.

## Use of Cursor Rules


When generating code, explanations, or suggestions, Copilot should always consult and apply the detailed rules and guidelines found in the `.github/Rules/` directory, in addition to any instructions in this file. The files in `.github/Rules/` take precedence and contain the most up-to-date and detailed standards for:

- Python coding standards
- Project structure
- VIKTOR SDK usage
- 3D modeling tips
- DynamicArray field visibility
- Testing and quality checks
- SCIA integration
- And other project-specific conventions

In addition, Copilot should reference the following important project files and directories for context and definitions:

- All files in `src/data_models/`:
	- `src/data_models/bridge_models.py`
	- `src/data_models/combination_models.py`
	- `src/data_models/geometry_data_models.py`
	- `src/data_models/geometry_models.py`
	- `src/data_models/idea_models.py`
	- `src/data_models/load_models.py`
	- `src/data_models/material_models.py`
	- `src/data_models/plotting_models.py`
	- `src/data_models/scia_models.py`
	- `src/data_models/vehicle_models.py`

- All files in `docs/`:
	- `docs/architecture.md`
	- `docs/code_style.md`
	- `docs/development_workflow.md`
	- `docs/pydantic_developer_guide.md`
	- `docs/testing_uitleg.md`

- Python coding standards
- Project structure
- VIKTOR SDK usage
- 3D modeling tips
- DynamicArray field visibility
- Testing and quality checks
- SCIA integration
- And other project-specific conventions    

If a rule or guideline is present in both this file and a `.github/Rules/` file, the `.github/Rules/` version is authoritative.

## General Guidance

- Always follow the standards and best practices described in `.github/Rules/`.
- If unsure about a rule, check the relevant `.mdc` or `.md` file in `.github/Rules/`.
- For enforcement, use automated tools (Ruff, Mypy, pre-commit hooks, CI workflows) as described in the quality and coding standards files.
- Keep this file concise; detailed and evolving rules should be maintained in `.github/Rules/`.

---

For any questions or to propose changes, update the relevant file in `.github/Rules/` and reference it here if needed.

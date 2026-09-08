# Code Verification Guardrails

When modifying code in this project, you MUST verify your changes before finishing your turn. Never rely solely on blind text-replacement scripts without verification.

## 1. Python Syntax Verification
- After modifying any `.py` file, you MUST verify the syntax compiles.
- Run: `python -m py_compile <path-to-file.py>`
- If the compilation fails with an `ImportError` or `SyntaxError` (or `NameError` if tested via execution), you must resolve it before notifying the user.

## 2. React / JSX Scope Verification
- After modifying a `.jsx` or `.tsx` file, you MUST explicitly ensure that all referenced variables and components are defined within the render scope.
- Since blind replacements can accidentally delete or misplace variable declarations (e.g., `imagesToShow`), always review the surrounding code context by reading the file before applying patches.
- If available in the environment, use `npm run lint` or check the Vite console output to confirm there are no `ReferenceError` exceptions.

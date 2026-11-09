# Testing and Security Rules

- Add regression tests for every corrected defect.
- Test success, rejection, timeout, cancellation and persistence failure paths where relevant.
- Validate authorization failures and secret redaction.
- Use Ruff for linting and Python compile checks.
- Build wheel and source distribution; validate archive integrity.
- Review dependencies and known vulnerabilities before release.
- Never place live credentials in fixtures, logs, workflow YAML or documentation.
- Do not suppress failing tests or security findings without a documented, approved exception.
- Report unexecuted checks honestly.

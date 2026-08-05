# Contributing to PiRadar

PiRadar is developed as a reliable appliance. Changes should be small, documented and testable on modest Raspberry Pi hardware.

Thank you for taking the time to help. Bug reports, documentation fixes,
hardware compatibility notes, accessibility improvements, and code changes are
all useful. You do not need to own the reference hardware to contribute; say
what environment you tested and what you could not verify.

## Before you start

- Search existing issues before opening a new one.
- For a larger change, open an issue first so the approach can be agreed before
  substantial work begins.
- Never post credentials, private location data, or security vulnerabilities in
  a public issue. Use the process in [SECURITY.md](SECURITY.md) for sensitive
  reports.

## Workflow

1. Open or select an issue with a clear outcome.
2. Create a focused branch from `main`.
3. Add tests for changed backend behaviour and manually verify UI changes at 800×480.
4. Update relevant specifications or ADRs when a contract or decision changes.
5. Open a pull request describing the change, validation and hardware impact.

Pull requests should target `main`. Maintainers may ask for a change to be split
when it combines unrelated outcomes.

## Local checks

```bash
PYTHONPATH=backend python3 -m unittest discover -s tests -v
python3 -m compileall -q backend
```

Do not commit API keys, precise private home locations, generated build output or local `config/piradar.json` files.

By contributing, you agree that your contribution is licensed under the
project's [MIT License](LICENSE).

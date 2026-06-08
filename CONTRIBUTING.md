# Contributing to provident-py

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Development Setup

This project uses [Nix](https://nixos.org/) for reproducible development environments and [Task](https://taskfile.dev/) as a task runner.

```bash
# Enter the development shell
nix develop

# List available tasks
task

# Install dependencies
uv sync
```

## Making Changes

1. Create a branch from `main`:

   ```bash
   git checkout -b feat/my-feature main
   ```

2. Make your changes and ensure everything passes:

   ```bash
   task check   # lint + format check + type check
   task test    # run tests
   ```

3. Commit with a [Conventional Commits](#commit-messages) message.

4. Open a pull request against `main`.

## Commit Messages

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope)!: description
```

- **type** (required): `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`
- **scope** (optional): a short module/context label, e.g. `client`, `auth`, `models`, `ci`
- **!** (optional): indicates a breaking change
- **description** (required): short summary in lowercase imperative mood

### Examples

```
feat(client): add async support
fix(auth): handle expired tokens
docs: update API reference
ci: add PR title linting
refactor(models)!: rename ChartDataResult fields
chore(deps): update httpx to 0.28
```

## Pull Requests

- **PR title** must follow the same Conventional Commits format as commit messages.
- Squash merging is the only allowed merge strategy. Your PR title becomes the commit message on `main`.
- All PRs require at least one approval.
- CI must pass before merging.

### PR Title Examples

```
feat(client): add retry logic for transient failures
fix: correct meter type mapping for cold water
docs: add async usage examples
```

## Code Style

- **Linting & formatting**: [Ruff](https://docs.astral.sh/ruff/) — `task check` / `task format`
- **Type checking**: [ty](https://docs.astral.sh/ty/) — included in `task check`
- **Tests**: [pytest](https://docs.pytest.org/) — `task test`

Run `task format` to auto-fix lint and formatting issues before committing.

## Branching Model

- `main` is the only long-lived branch.
- All changes go through pull requests — direct pushes to `main` are blocked.
- Branch naming convention: `type/short-description` (e.g. `feat/async-client`, `fix/token-expiry`).

## Release Process

Releases are automated. Pushing a version tag (`v*`) triggers a PyPI publish via the `Release` workflow.

## License

By contributing, you agree that your changes will be licensed under the [MIT License](LICENSE).

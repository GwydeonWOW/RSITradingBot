# Contributing Guide

This project follows the **Git Flow** branching strategy. All contributors must adhere to these conventions.

## Branch Strategy

| Branch | Purpose | Merges Into |
|---|---|---|
| `main` | Production-ready code. Protected. | -- |
| `develop` | Integration branch for features. Protected. | `main` (via release) |
| `feature/*` | New features or enhancements. | `develop` |
| `release/*` | Release preparation and stabilization. | `main` + `develop` |
| `hotfix/*` | Emergency fixes for production. | `main` + `develop` |

## Branch Naming

Format: `<type>/<TASK-ID>-<short-description>`

Examples:
- `feature/RSI-001-add-backtesting-engine`
- `hotfix/RSI-042-fix-order-duplicate`
- `release/v1.0.0`

No slashes in the description portion. Use lowercase with hyphens.

## Commit Messages

Format: `<type>(<scope>): <description>`

Types:
- `feat` -- New feature
- `fix` -- Bug fix
- `docs` -- Documentation only
- `refactor` -- Code restructuring with no behavior change
- `test` -- Adding or updating tests
- `chore` -- Maintenance (deps, configs, tooling)
- `ci` -- CI/CD pipeline changes

Examples:
```
feat(backtesting): add RSI strategy backtesting engine
fix(orders): prevent duplicate order submission
docs(api): update endpoint descriptions
```

## Workflow

### Starting a Feature

```bash
git checkout develop
git pull origin develop
git checkout -b feature/RSI-001-short-description
```

### Finishing a Feature

1. Open a pull request targeting `develop`.
2. Ensure CI passes and at least one reviewer approves.
3. Merge using a merge commit (no squash, no rebase).
4. Delete the feature branch after merge.

### Releases

1. Create `release/vX.Y.Z` from `develop`.
2. Bump version, update changelog, fix any last issues.
3. Open a PR to `main`. After merge, tag `vX.Y.Z`.
4. Merge the release branch back into `develop`.

### Hotfixes

1. Create `hotfix/<TASK-ID>-description` from `main`.
2. Open a PR to `main`. After merge, tag `vX.Y.PATCH`.
3. Merge the hotfix branch back into `develop`.

## Pull Request Checklist

- [ ] Branch name follows naming convention.
- [ ] Commit messages follow conventional commit format.
- [ ] No merge conflicts with the target branch.
- [ ] Tests pass (or tests have been added for new behavior).
- [ ] No secrets or credentials in the diff.

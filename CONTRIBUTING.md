# Contributing to The Gold Box

Thank you for your interest in contributing to The Gold Box! This document outlines the development workflow and guidelines for contributing to the project.

## Development Workflow

The Gold Box uses a **feature branch** model for development. This means all development work happens on feature branches, which are then merged back into `main` when complete.

### Overview

1. Create a feature branch for your work
2. Make and test your changes
3. Update version numbers and changelog
4. Merge the feature branch back to `main`
5. Tag and trigger release

## Step-by-Step Process

### 1. Create a Feature Branch

Create a new branch from `main` with a descriptive name:

```bash
git checkout main
git pull origin main
git checkout -b feature/0.3.9-the-foundation
```

**Branch Naming Convention:**
- `feature/x.y.z-description` - For new features (e.g., `feature/0.3.9-the-foundation`)
- `fix/x.y.z-description` - For bug fixes (e.g., `fix/0.3.8-security-patch`)
- `refactor/description` - For code refactoring

### 2. Make and Test Your Changes

Develop your feature on the feature branch. Before merging, ensure:

- [ ] Code follows project structure and conventions
- [ ] Update function_check.sh with new AI functions (if applicable)
- [ ] Update server_test.sh with new security middleware (if applicable)
- [ ] All existing tests pass
- [ ] New functionality is tested (if applicable)
- [ ] No console errors in browser
- [ ] Backend server starts without errors
- [ ] Changes work in Foundry VTT

Run backend tests:
```bash
cd backend/testing
./server_test.sh
```

### 3. Update Version and Changelog

#### Update module.json
Update the version number in `module.json`:
```json
{
  "version": "0.3.9",
  "download": "https://github.com/ssjmarx/The-Gold-Box/releases/download/0.3.9/module.zip",
  "manifest": "https://github.com/ssjmarx/The-Gold-Box/releases/download/0.3.9/module.json"
}
```

#### Update CHANGELOG.md
Add a new section to `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:

```markdown
## [0.3.9] - YYYY-MM-DD

### New Features
- Feature description here

### Bug Fixes
- Bug fix description here

### Changes
- Any breaking changes or notable modifications
```

### 4. Commit Your Changes

Use descriptive commit messages:
```bash
git add .
git commit -m "feat: implement post_message tool function"
```

**Commit Message Guidelines:**
- Use imperative mood ("add feature" not "added feature")
- Start with one of these prefixes:
  - `feat:` - New feature
  - `fix:` - Bug fix
  - `docs:` - Documentation only changes
  - `refactor:` - Code refactoring
  - `test:` - Adding or updating tests
  - `chore:` - Maintenance tasks

### 5. Merge to Main

When your feature is complete and tested:

```bash
git checkout main
git merge feature/0.3.9-the-foundation
git push origin main
```

**Optional: Delete the feature branch after merging**
```bash
git branch -d feature/0.3.9-the-foundation
git push origin --delete feature/0.3.9-the-foundation
```

### 6. Tag and Trigger Release

Create and push a version tag to trigger the GitHub release workflow:

```bash
git tag v0.3.9
git push origin v0.3.9
```

**How the Release Workflow Works:**

The `.github/workflows/release.yml` workflow automatically triggers when a tag matching `v*` is pushed. It will:

1. Create a `module.zip` file excluding `.git` and `.github` directories
2. Update URLs in `module.json` to point to the specific version
3. Create a GitHub release with:
   - The version tag
   - Release notes linking to CHANGELOG.md
   - Both `module.json` and `module.zip` as assets

**Important:** The release workflow runs automatically. Just push the tag and GitHub handles the rest!

## Version Management

The Gold Box follows [Semantic Versioning](https://semver.org/spec/v2.0.0/):

- **MAJOR** (x.y.z) - Incompatible API changes
- **MINOR** (0.x.y) - New features, backwards compatible
- **PATCH** (0.0.z) - Bug fixes, backwards compatible

Current release cycle: 0.3.x series focuses on the comprehensive AI tool suite.

## Testing Checklist

Before merging any changes, verify:

### Backend Tests
```bash
cd backend/testing
./server_test.sh
./function_check.sh
```

### Manual Testing in Foundry VTT
- [ ] Module loads without errors
- [ ] Settings menu opens correctly
- [ ] Backend connection works
- [ ] Core functionality (AI chat) works
- [ ] Any new features work as expected
- [ ] Error handling works (test edge cases)

## Development Environment Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

### Frontend
The frontend requires Foundry VTT to run. Link the module to your Foundry `Data/modules/` directory:

```bash
# Linux/macOS
ln -s /path/to/The-Gold-Box ~/.local/share/FoundryVTT/Data/modules/the-gold-box

# Windows
# Create a junction or copy the directory
```

## Code Quality Guidelines

- Follow existing code structure and patterns
- Use descriptive variable and function names
- Add comments for complex logic
- Keep functions focused and modular
- Test new functionality before committing

## Future Automation (Phase 2)

This manual workflow will be enhanced with full CI/CD automation starting with **Patch 0.4.1** (The Automation Update), which will include:

- Automated testing on every pull request
- Automated linting (ESLint, Pylint)
- Branch protection rules
- Enhanced release workflow with Foundry VTT Developer API integration

See [ROADMAP.md](ROADMAP.md) for the complete Phase 2 plan.

## Getting Help

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/ssjmarx/The-Gold-Box/issues)
- **Documentation**: See [README.md](README.md), [USAGE.md](USAGE.md), and [ROADMAP.md](ROADMAP.md)
- **Discussions**: Use GitHub Discussions for questions and ideas

## License

By contributing to The Gold Box, you agree that your contributions will be licensed under the same license as the project: [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](LICENSE).

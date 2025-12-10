name: factory-dev
description: Build, validate, and manage Factory artifacts (skills, droids, commands, hooks)
argument-hint: <subcommand> [options]
---

# Factory Development CLI

Build, validate, and manage Factory artifacts with expert guidance.

## Subcommand: $ARGUMENTS

## Available Subcommands

| Subcommand | Description |
|------------|-------------|
| `validate <path>` | Validate a droid, skill, command, or hook file |
| `validate-all` | Validate all Factory artifacts in current scope |
| `build skill <name>` | Scaffold a new skill with best practices |
| `build droid <name>` | Scaffold a new custom droid |
| `build command <name>` | Scaffold a new slash command |
| `lint` | Run markdownlint on all Factory markdown files |
| `docs <topic>` | Look up Factory documentation |
| `help` | Show this help message |

## Instructions

Based on the subcommand provided in `$ARGUMENTS`, execute the appropriate action:

### For validate path

1. Use the `factory-validate` skill to validate the specified file
2. Check YAML frontmatter syntax and required fields
3. Verify tool names are valid (Read, Edit, Execute, etc.)
4. Check model references are valid
5. Lint markdown for formatting issues
6. Report all errors and warnings

### For validate-all

1. Scan `~/.factory/droids/`, `~/.factory/skills/`, `~/.factory/commands/`
2. Also scan `.factory/` in current project if exists
3. Validate each artifact and compile a report

### For build skill, droid, or command

1. Use the `factory-scaffold` skill
2. Look up Context7 docs first, then Factory docs
3. Generate well-structured artifact following best practices
4. Include comprehensive documentation

### For lint

1. Run `markdownlint` on all `.md` files in Factory directories
2. Report issues with file paths and line numbers

### For docs topic

1. Use the `factory-docs` skill
2. Query Context7 first for Factory documentation
3. Fall back to Factory docs website if needed
4. Summarize relevant documentation

## Context7 Integration

Always try Context7 first for documentation:

```yaml
context7___resolve-library-id: "factory droid cli"
context7___get-library-docs: topic based on query
```

If Context7 doesn't have the docs, fall back to:

- [Custom Droids](https://docs.factory.ai/cli/configuration/custom-droids)
- [Skills](https://docs.factory.ai/cli/configuration/skills)
- [Slash Commands](https://docs.factory.ai/cli/configuration/custom-slash-commands)

## Validation Rules Reference

### Droid Validation

- Required frontmatter: `name`, `description`
- Optional: `model` (inherit or valid model ID), `tools` (array of valid tool IDs)
- Name must be lowercase with hyphens/underscores only
- Body must be non-empty

### Skill Validation

- Required frontmatter: `name`, `description`
- Must have `SKILL.md` or `skill.md` in a directory
- Supporting files optional but recommended

### Command Validation

- For markdown: frontmatter `description` recommended, `argument-hint` optional
- For executables: must have valid shebang
- `$ARGUMENTS` placeholder supported in markdown

### Valid Tool IDs

`Read`, `LS`, `Grep`, `Glob`, `Create`, `Edit`, `MultiEdit`, `ApplyPatch`, `Execute`, `WebSearch`, `FetchUrl`, `TodoWrite`, `Task`

### Valid Model References

- `inherit` - use parent session model
- Built-in: `claude-sonnet-4-5-20250929`, `claude-opus-4-5-20251101`, etc.
- Custom: `custom:<model-name>` for BYOK models
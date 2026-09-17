# AGENTS.md

This file defines how automated agents (and human contributors) must work in this repository.

## 1. Project Purpose

`serde-onnx` is a Rust extension crate for `serde`, analogous to `serde_json` and `serde_yaml`, that provides serialization and deserialization of Rust models to and from the **ONNX format**.

- ONNX is defined via Protocol Buffers. Treat `.proto` definitions as the source of truth.
- Reference documentation: https://github.com/onnx/onnx/tree/main/docs
  - Operators: https://github.com/onnx/onnx/blob/main/docs/Operators.md
  - IR (Model, Graph, Node, Tensor, etc.): https://github.com/onnx/onnx/blob/main/docs/IR.md
  - Versioning and opsets: https://github.com/onnx/onnx/blob/main/docs/Versioning.md
- Goal: users define Rust structs/enums with `#[derive(Serialize, Deserialize)]` and call `serde_onnx::to_bytes` / `serde_onnx::from_bytes` (or equivalent API) to produce/consume valid ONNX protobuf bytes that are loadable by `onnx`, `onnxruntime`, and other compliant runtimes.

## 2. Language Policy

- **All documentation and code MUST be written in English.** This includes comments, doc-comments (`///`, `//!`), commit messages, PR/issue titles and bodies, OpenSpec artifacts (`proposal.md`, `spec.md`, `design.md`, `tasks.md`), `CHANGELOG.md`, and `README.md`.
- Do not mix languages. Review generated files for accidental non-English strings.

## 3. OpenSpec Workflow (spec-driven)

This repository uses OpenSpec with the `spec-driven` schema (`proposal -> specs -> design -> tasks`).

- Do not edit `openspec/specs/` directly. All spec changes go through an OpenSpec change: `openspec new change "<kebab-case-name>"`.
- Every change must have at least `proposal.md`, `specs/<capability>/spec.md` (delta spec), and `tasks.md`. Add `design.md` when the change needs architecture or API decisions.
- Validate before applying or archiving: `openspec validate --strict` and `openspec status --change "<name>" --json`.
- Apply workflow is explicit: planning (`/opsx-propose` or `openspec new change`) is separate from implementation (`/opsx-apply`). Do not implement during planning.

## 4. TDD Requirement for Every Change

**All tasks MUST be written using the globally available `tdd` skill** (`~/.agents/skills/tdd/SKILL.md` and `~/.claude/skills/tdd/SKILL.md`).

### 4.1 Task Authoring Rules

- `tasks.md` must follow the TDD skill workflow: **Planning -> Tracer Bullet -> Incremental RED-GREEN-REFACTOR loop -> Refactor**.
- Use **vertical slices**, not horizontal slices. Each task is one `RED -> GREEN` cycle: one test that validates one observable behavior through the public API, followed by the minimal implementation that makes it pass.
- Do NOT write all tests first and then all implementation. Order tasks as `test1 -> impl1 -> test2 -> impl2 -> ...`.

### 4.2 ONNX Operator Coverage Rule

- **Every ONNX operator created MUST be validated by at least one test.** A task that introduces an operator without a corresponding test is invalid.
- Tests must verify behavior through the public `serde_onnx` API (e.g., serialize a Rust struct to ONNX bytes and deserialize back, or compare against `onnx` reference bytes), not by inspecting internal protobuf structs directly or mocking internals.
- Prefer integration-style tests that round-trip through `serde` and produce bytes that can be validated with the ONNX checker / `onnx` Python package when feasible. Mock only at system boundaries (filesystem, external `onnx` checker subprocess) per `tdd/mocking.md`.
- Each operator spec in `specs/<capability>/spec.md` must have a corresponding `tasks.md` entry that references the test that validates it.

### 4.3 Test Quality Checklist (per cycle)

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features
```

## 5. Dual-Worktree / Dual-Branch Strategy

Every logical change MUST be split across **two git worktrees / branches** that follow Conventional Commits naming.

### 5.1 Branch Naming

```
<type>/<kebab-case-name>-openspec
<type>/<kebab-case-name>-code
```

- `<type>` is a Conventional Commit type: `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`.
- `<kebab-case-name>` is the same stem for both branches (e.g., `add-conv-operator`).
- Example pair for a new operator `Conv`:
  - `feat/add-conv-operator-openspec`
  - `feat/add-conv-operator-code`

> Note: the worktree name equals the branch name. The suffix `-openspec` vs `-code` is the only difference.

### 5.2 Worktree Layout

Create worktrees from `main` (or the current base branch):

```bash
# from repository root on branch main
git worktree add ../serde-onnx-feat-add-conv-operator-openspec -b feat/add-conv-operator-openspec
git worktree add ../serde-onnx-feat-add-conv-operator-code     -b feat/add-conv-operator-code
```

Or if branches already exist:

```bash
git worktree add ../serde-onnx-feat-add-conv-operator-openspec feat/add-conv-operator-openspec
git worktree add ../serde-onnx-feat-add-conv-operator-code     feat/add-conv-operator-code
```

### 5.3 Content Split

| Worktree / Branch | Allowed paths | Contains |
|---|---|---|
| `*-openspec` | `openspec/**`, `CHANGELOG.md` | `openspec new change` output, `proposal.md`, `specs/**/spec.md`, `design.md`, `tasks.md`, spec deltas, and the `CHANGELOG.md` entry for the change. No source code. |
| `*-code` | everything except `openspec/**` and `CHANGELOG.md` (i.e., `src/**`, `tests/**`, `Cargo.toml`, `Cargo.lock`, `.gitignore`, `README.md` (code docs), `AGENTS.md` itself) | Rust implementation, unit/integration tests, benchmarks, and configuration. No spec files. |

Rules:

- When `openspec new change "<name>"` is run, execute it **inside the `-openspec` worktree** and commit there. The initial change commit must include the scaffold plus `CHANGELOG.md` update if applicable.
- Code changes, including TDD tests for operators, are committed **only in the `-code` worktree**.
- Never mix paths: a commit on `*-openspec` must not touch `src/`; a commit on `*-code` must not touch `openspec/`.
- Keep both branches rebased on the same base `main` commit so the pair can be reviewed together.

### 5.4 Commits

- Use Conventional Commits: `type(scope): description` (e.g., `feat(onnx): add Conv operator serialization`).
- Commits on `*-openspec` use scope `spec` or `openspec` (e.g., `docs(spec): add Conv operator spec and tasks`).
- Commits on `*-code` use scope reflecting the crate area (e.g., `feat(codec): implement Conv operator codec with TDD`).
- Each worktree must have at least one commit. Do not force-push without review.

## 6. GitHub Issue and Pull Request Workflow

At the end of a change, open **two Pull Requests** and **one Issue** that ties them together.

### 6.1 Issue

- Title: same stem as the change, in English, e.g., `[feat] Add Conv operator support`.
- Body must explain: motivation, scope, link to ONNX docs section, list of operators/specs added, TDD test summary, and links to both PRs.
- Label with `enhancement` / `feat` as appropriate.

```bash
gh issue create --title "[feat] Add Conv operator support" \
  --body "Motivation: ...\n\nSpec PR: #<n>\nCode PR: #<m>\n\nONNX ref: https://github.com/onnx/onnx/blob/main/docs/Operators.md#Conv\nTests: tracer bullet + incremental RED-GREEN for Conv forward pass"
```

### 6.2 Pull Requests

- **Spec PR**: base `main`, head `<type>/<name>-openspec`, title `docs(spec): <description>`. Body references the Issue (`Closes #<issue>` or `Related to #<issue>`) and lists `openspec/` artifacts changed.
- **Code PR**: base `main`, head `<type>/<name>-code`, title `<type>(<scope>): <description>`. Body references the Issue, describes TDD cycles executed, and includes `cargo test` output summary.
- Both PRs must cross-reference each other and the Issue.
- Use draft PRs while `openspec validate --strict` is not green.

```bash
gh pr create --base main --head feat/add-conv-operator-openspec \
  --title "docs(spec): add Conv operator spec and tasks" \
  --body "Related to #<issue>\n\nOpenSpec change: add-conv-operator\nArtifacts: proposal, specs/operator-conv/spec.md, tasks.md (TDD vertical slices)"

gh pr create --base main --head feat/add-conv-operator-code \
  --title "feat(codec): implement Conv operator with TDD" \
  --body "Closes #<issue>\n\nImplements tasks from add-conv-operator via TDD:\n- RED: test Conv round-trip -> fail\n- GREEN: minimal codec -> pass\n- Incremental: strides, pads, dilations\n\n\`cargo test\` : all green"
```

## 7. Rust and Serde Conventions

- Edition 2024, `cargo fmt` and `cargo clippy -- -D warnings` must pass on the `-code` branch.
- Public API should mirror `serde_json` ergonomics where sensible (`to_bytes`, `from_bytes`, `to_writer`, `from_reader`).
- Use `prost` or `onnx` protobuf bindings for the wire format; do not hand-roll protobuf encoding.
- Keep modules deep and interfaces small per `tdd/deep-modules.md`. Serde `Serializer`/`Deserializer` impls are internal; expose only the crate-level functions and error types.

## 8. Validation Checklist Before Opening PRs

- [ ] `openspec validate --strict` passes on `*-openspec` worktree
- [ ] `cargo test` passes on `*-code` worktree, including the per-operator TDD tests
- [ ] `cargo fmt --check` and `cargo clippy` pass
- [ ] All docs/code/comments are in English
- [ ] Both worktrees have conventional branch names and at least one commit each
- [ ] Issue + 2 PRs are cross-linked

## 9. Example End-to-End Session

```bash
# 1. Start from main
git checkout main && git pull

# 2. Create the dual worktrees for feat/add-relu-operator
git worktree add ../serde-onnx-feat-add-relu-operator-openspec -b feat/add-relu-operator-openspec
git worktree add ../serde-onnx-feat-add-relu-operator-code     -b feat/add-relu-operator-code

# 3. Planning in -openspec worktree
cd ../serde-onnx-feat-add-relu-operator-openspec
openspec new change "add-relu-operator"
# edit proposal.md, specs/operator-relu/spec.md, design.md, tasks.md (tasks use TDD vertical slices, one test per operator behavior)
openspec validate --strict
git add openspec/ CHANGELOG.md && git commit -m "docs(spec): add Relu operator spec and TDD tasks"

# 4. Implementation in -code worktree (TDD)
cd ../serde-onnx-feat-add-relu-operator-code
# for each task in tasks.md: RED (write one test) -> GREEN (minimal code) -> REFACTOR
cargo test  # must include Relu operator round-trip test
git add src/ tests/ Cargo.toml && git commit -m "feat(codec): implement Relu operator with TDD"

# 5. Push and open GitHub artifacts
git push -u origin feat/add-relu-operator-openspec
git push -u origin feat/add-relu-operator-code
gh issue create --title "[feat] Add Relu operator" --body "..."
gh pr create --head feat/add-relu-operator-openspec ...
gh pr create --head feat/add-relu-operator-code ...
```

# AegisPR Agent Stages

## Orchestrator

Controls the state machine: ingest, analyze, impact, hypotheses, test generation, base execution, head execution, comparison, and report. It is the only stage allowed to call tools.

## Repository intelligence

Detects languages, framework, package manager, existing test framework, install command, test command, build command, configuration files, and changed files.

## Change and impact analysis

Combines the exact Git diff with reference scanning to create a bounded dependency neighborhood. The graph explains why unchanged files might be affected.

## Hypothesis and test generation

Nemotron first states a testable risk, then emits a framework-native test in strict JSON. Hypothesis IDs remain linked to generated test IDs throughout execution and reporting.

## Sandbox execution

The orchestrator checks file paths and command prefixes, then runs generated code in a container with dropped Linux capabilities, no new privileges, process limits, CPU and memory limits, a read-only root filesystem, and no test-time network.

## Differential verification

The same test runs against the base and head commits. A pure comparison function classifies results. This stage cannot invent confidence scores.

## Root cause and repair

Regression evidence can be used in a later model pass to propose the smallest reasonable patch. A repair is never marked verified until existing tests, generated tests, build, and configured type or lint checks pass.

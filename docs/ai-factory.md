# AI Software Development Factory — Reference

## Overview

A factory com **2 workflows**, **9 roles estáveis**, **4 capability levels**, **issue handling** e **re-planning automático**.

**Princípio central:** Substituir "novo agente para cada variação" por **roles claros + capability levels + orchestration inteligente**.

---

## Core Principles

### 1. Specification ≠ Execution
- **Spec Workflow:** Define WHAT/WHY
- **Dev Workflow:** Define HOW/BUILD/PROVE/ASSESS
- Desacopladas. Spec não faz refinamento técnico específico do codebase.

### 2. Issues Surgem. Lidar Com Elas É Parte Do Design
- Erros de infraestrutura, bugs, limitações técnicas, security issues descobertos
- Retry loops automáticos para issues simples
- Escalation intelligent para issues complexas
- Re-planning quando necessário

### 3. Poucos Roles + Capability Levels
```
Evite:  Code Simple, Code Complex, Test Basic, Test Deep, Security Triage, Security Deep
Prefira: Code Worker (simple/standard/complex)
         Test Engineer (simple/standard/complex)
         Security Reviewer (shallow/standard/deep)
```

### 4. Orchestrator Como Decision Layer
- Não faz trabalho especializado
- Escolhe: modelo, capability level, budget, timeout, paralelização
- Baseia-se em Technical Assessment do Technical Planner

### 5. ADR Condicional
- Criada apenas quando houver decisão técnica significativa
- Integrada ao Technical Planner workflow
- Validada por Code Reviewer

---

## Part 1: Specification Workflow

### Flow Sequencial
```
Request/Idea
    ↓
Spec Agent
├─ Produz: spec, plan, tasks, acceptance criteria, definition of done
├─ Usa: SpecKit
├─ NÃO faz: refinamento técnico do codebase
└─ Output: Draft Spec
    ↓
Requirements Reviewer
├─ Valida: clarity, completeness, consistency, testability, edge cases
├─ Verifica: Acceptance Criteria bem definido?
├─ Verifica: Definition of Done claro?
├─ Se REJECT → volta para Spec Agent
└─ Se APPROVE → passa para Development
    ↓
[Approved Spec + Acceptance Criteria + Definition of Done]
```

**Outputs críticos do Spec Agent:**
```yaml
spec:
  title: "OAuth Integration"
  description: "Add OAuth authentication to user service"
  business_value: "Allow users to login with Google/GitHub"

acceptance_criteria:
  - "User can authenticate via Google OAuth"
  - "Token refresh works within the flow"
  - "Logout clears session and token"
  - "Unauthenticated access to protected endpoints returns 401"

definition_of_done:
  - Code review passed
  - Unit tests pass (>80% coverage)
  - Integration tests pass
  - E2E tests pass (browser flow)
  - Security review complete
  - Documentation updated
  - PR merged to main

edge_cases:
  - Expired tokens during long operations
  - Concurrent login attempts
  - OAuth provider unavailable
  - Network timeout during token refresh
```

---

## Part 2: Development Workflow (Com Issue Handling)

### High-Level Flow

```
[Approved Spec]
    ↓
PLANNING PHASE
├─ Technical Planner
│  ├─ Refino técnico
│  ├─ ADR se necessário
│  └─ Assessment (complexity, risks, security surface)
└─ Orchestrator
   └─ Decisões de execução (models, levels, budget, parallelization)
    ↓
EXECUTION PHASE (com retry loops)
├─ Code Worker + Code Reviewer + Test Engineer (paralelo)
├─ Test Runner (valida, retries se necessário)
├─ Security Reviewer (análise, feedback)
└─ Documentation (se required)
    ↓
[All Checks Passed?]
├─ YES → PR Ready ✓
└─ NO → Escalate (Retry/Fix/Re-plan)
```

---

## Part 3: The 9 Roles (Responsibility Matrix)

| # | Role | Responsabilidade | Input | Output | Sequência |
|---|------|------------------|-------|--------|-----------|
| 1 | **Spec Agent** | Definir o quê e por quê | Request/Idea | Spec, tasks, AC, DoD | Spec Phase 1º |
| 2 | **Requirements Reviewer** | Validar requisitos | Spec | Approve/Reject | Spec Phase 2º |
| 3 | **Orchestrator** | Decisões de execução | Technical Assessment | Execution plan (models, levels, budget) | Dev Phase 1º |
| 4 | **Technical Planner** | Refino técnico, arquitetura, ADR | Approved Spec + Codebase | Technical Plan + Assessment + ADR? | Dev Phase 2º |
| 5 | **Code Worker** | Implementação e unit tests | Technical Plan | Code + implementation tests | Dev Phase 3º (paralelo) |
| 6 | **Code Reviewer** | Validar código | Code | Approve/Reject | Dev Phase 3º (paralelo) |
| 7 | **Test Engineer** | Estratégia e implementação de testes | AC + DoD + Technical Plan | Test suite (unit/integration/E2E/regression) | Dev Phase 3º (paralelo) |
| 8 | **Test Runner** | Executar testes, retry e diagnosticar | Test suite | Evidence + pass/fail | Dev Phase 4º |
| 9 | **Security Reviewer** | Análise de segurança | Code + Security surface | Security assessment + Approve/Reject | Dev Phase 5º |

---

## Part 4: Capability Levels (Execution Control)

### Code Worker
```
Capability Levels: simple | standard | complex

simple:
  - Model: claude-3.5-sonnet (cost optimized)
  - Max tokens: 4k
  - Context: Single file changes, localized fixes
  - Iterations: 1-2
  - Examples: Add parameter, fix typo, add logging

standard:
  - Model: claude-opus-4 (balanced)
  - Max tokens: 8k
  - Context: Multi-file changes, feature implementations
  - Iterations: 2-3
  - Examples: Authentication feature, API endpoint

complex:
  - Model: claude-opus-4-extended (full reasoning)
  - Max tokens: 16k+
  - Context: Distributed system changes, performance optimization
  - Iterations: 3-5 + retry loops
  - Examples: Query optimization, concurrency handling, distributed cache
```

### Code Reviewer
```
Capability Levels: shallow | standard | deep

shallow:
  - Check: syntax, basic logic, obvious bugs
  - Time: ~5 min
  - Tool access: Limited

standard:
  - Check: correctness, architecture adherence, maintainability, standards
  - Time: ~15 min
  - Tool access: Full context, git history
  - Checks: Code style, regressions, ADR adherence

deep:
  - Check: Security implications, performance impact, scalability
  - Time: ~30 min
  - Tool access: Codebase analysis, dependency audit
  - Checks: Vulnerability surface, memory/perf profiling, architectural trade-offs
```

### Test Engineer
```
Capability Levels: simple | standard | complex

simple:
  - Tests: unit only
  - Scope: single component
  - Examples: Utility function tests

standard:
  - Tests: unit + integration
  - Scope: component + API boundaries
  - Examples: Feature with database interactions

complex:
  - Tests: unit + integration + E2E + regression
  - Scope: full feature flow + system-wide impact
  - Concurrency tests, load tests, chaos testing
  - Examples: OAuth flow with token refresh, concurrent updates
```

### Security Reviewer
```
Capability Levels: shallow | standard | deep

shallow:
  - Check: Obvious vulnerabilities (hardcoded secrets, SQL injection patterns)
  - Time: ~10 min
  - No third-party scanning

standard:
  - Check: Auth/authz, sensitive data handling, input validation
  - Check against: OWASP Top 10, CWE common patterns
  - Time: ~20 min
  - Tool access: SAST, dependency scan

deep:
  - Check: All above + cryptography, API security, supply chain risks
  - Check against: NIST, industry standards
  - Time: ~40 min
  - Tool access: Dynamic analysis, threat modeling, penetration testing mindset
```

---

## Part 5: Technical Planner & ADR

### Technical Planner Responsibilities

**Input:** Approved Spec + Codebase + Architecture

**Process:**
```
1. Analyze Spec
   ├─ Map to existing components
   ├─ Identify affected services, APIs, databases
   └─ Spot dependencies and risks

2. Produce Technical Plan
   ├─ Implementation strategy
   ├─ File/component changes
   ├─ Database schema changes (if any)
   ├─ API contracts
   ├─ Event/message changes
   ├─ Potential parallelization
   └─ Technical subtasks (ordered)

3. Produce Assessment
   └─ complexity: simple | standard | complex
   └─ technical_risk: low | medium | high
   └─ architecture_impact: low | medium | high
   └─ test_scope: {unit, integration, e2e, regression}
   └─ security_surface: {authentication, authorization, sensitive_data, external_input}
   └─ documentation_required: boolean

4. Decide: ADR Needed?
   ├─ Non-conventional architecture decision?
   ├─ Important trade-off?
   ├─ Workaround for constraint?
   ├─ Legacy system limitation?
   ├─ Unusual bug fix?
   └─ If YES → Create ADR before Code Worker starts
```

### ADR (Architecture Decision Record) — When & How

**ADR is appropriate for:**
- Non-conventional architectural decisions
- Trade-offs (e.g., "make consumer idempotent" for duplicate events)
- Legacy system constraints
- Integration limitations
- Significant workarounds

**ADR is NOT needed for:**
- Simple fixes (NullReference → add validation)
- Obvious optimizations (Slow query → add index)
- Code changes without architecture impact

**ADR Flow:**
```
Technical Planner determines: ADR needed?
    ├─ YES → Create ADR (decision, rationale, trade-offs, alternatives considered)
    │        ├─ Code Reviewer validates adherence to ADR
    │        └─ ADR becomes source of truth during implementation
    └─ NO  → Skip directly to Code Worker
```

**ADR Template:**
```yaml
title: "Idempotent Consumer for Duplicate Event Handling"
context: |
  Producer sends duplicate events (unfixable due to external system constraint).
  Consumer must handle duplicates gracefully.

decision: |
  Implement idempotency in the consumer by tracking processed event IDs
  in a persistent deduplication table (PostgreSQL).

rationale: |
  - Producer cannot be changed
  - At-most-once semantics required for correctness
  - Persistent storage allows recovery across restarts

trade_offs:
  - Additional database table (minimal storage)
  - Deduplication query on every message (microseconds impact)
  - Retention policy needed (events older than X days cleaned)

alternatives_considered:
  - In-memory deduplication: Lost on restart
  - Distributed cache (Redis): Operational complexity, potential consistency issues
  - Change producer: Not feasible (external system)

approved_by: "Technical Planner, Code Reviewer"
date: "2025-01-15"
```

---

## Part 6: Issue Detection & Handling

### Issues That Emerge (6 Categories)

```
1. INFRASTRUCTURE ISSUES
   └─ Container timeout, DB connection pool, Redis miss, API rate limit, network timeout

2. TECHNICAL LIMITATIONS
   └─ Performance SLA miss, memory overflow, circular dependency, lock contention

3. LOGIC BUGS
   └─ NullReferenceException, off-by-one, race condition, state machine error, deadlock

4. SECURITY ISSUES
   └─ SQL injection, CORS misconfiguration, token expiry bug, sensitive data logged

5. DATA-DRIVEN EDGE CASES
   └─ Test data incomplete, legacy format incompatible, concurrent update duplicates

6. THIRD-PARTY INTEGRATION
   └─ API deprecated, webhook duplicate delivery, OAuth token refresh loop
```

### Detection Points (Who Catches What)

```
Code Worker
    └─ Local validation → linting, type check, build

Code Reviewer
    ├─ Architecture violation
    ├─ Logic bug
    └─ Standard violation

Test Engineer + Test Runner
    ├─ Unit test fail → logic bug or test error
    ├─ Integration test fail → infrastructure, API, or data
    ├─ E2E test fail → performance, timing, or backend
    └─ Regression fail → unintended side effects

Security Reviewer
    ├─ Vulnerability
    └─ Design conflict with security requirements
```

---

## Part 7: Retry Loops & Escalation

### Retry Strategy by Issue Type

#### Code Quality Issues
```
Code generation
    ├─ Linting/Type Check Error
    │  └─ Retry: Code Worker local fix (1-3 attempts)
    ├─ Build Error
    │  └─ Retry: Code Worker fix dependency/config
    └─ If persists → Escalate to Code Reviewer
```

#### Code Review Issues
```
Code Reviewer rejects
    ├─ Simple (null check, off-by-one)
    │  └─ Retry: Code Worker 1-2x, re-review immediately
    ├─ Complex (race condition, state machine)
    │  └─ Escalate: Needs Technical Planner input
    └─ Architectural (violates plan)
       └─ Decision: Fix code OR update Technical Plan
```

#### Test Failures (Deterministic)
```
Test fails reproducibly
    ├─ Unit test: Likely logic bug
    │  └─ Send to Code Worker: "Unit test X failed. Expected Y, got Z."
    ├─ Integration test: Logic or data state issue
    │  └─ Send to Code Worker with database state snapshot
    └─ Code Worker fixes → Code Reviewer validates → Test Runner re-runs
```

#### Test Failures (Transient/Infrastructure)
```
Test fails intermittently
    ├─ Likely: network timeout, container restart, race condition in test
    └─ Retry Strategy: Exponential backoff
       ├─ Attempt 1: immediate
       ├─ Attempt 2: wait 2s, retry
       ├─ Attempt 3: wait 4s, retry
       ├─ Attempt 4: wait 8s, retry
       ├─ Attempt 5: wait 16s, retry
       └─ If still fails → Escalate to Infrastructure team
```

#### E2E Test Failures
```
Browser E2E fail
    ├─ Page load timeout (>30s)
    │  ├─ Diagnose: Slow query? N+1? Unoptimized asset?
    │  ├─ Escalate: Code Worker performance optimization
    │  └─ Security Reviewer: Check DoS-ability
    ├─ UI state error (element not found, stale)
    │  ├─ Fix: Test Engineer refine waits OR Code Worker fix race condition
    │  └─ Retry: Re-run
    └─ Backend failure (500 error, assertion fail)
       ├─ Evidence: Server logs, database state
       ├─ Escalate: Code Worker + Test Engineer (integration contract broke)
       └─ Retry: After fix
```

#### Security Issues
```
Vulnerability found
    ├─ CRITICAL (SQL injection, auth bypass, exposed secrets)
    │  ├─ Action: STOP. Code Worker immediate fix.
    │  ├─ Code Reviewer: Mandatory deep review
    │  └─ Security Reviewer: Full re-audit
    ├─ MEDIUM (weak password policy, excessive logging)
    │  ├─ Code Worker fix OR Technical Planner ADR
    │  └─ Re-audit before merge
    └─ LOW (code smell, future concern)
       └─ Note & merge (but prioritize in follow-up)
```

### Escalation Decision Tree

**WHEN TO RETRY (Local Fix):**
```
Issue found
    ├─ Deterministic & reproducible? YES
    ├─ Root cause in current code? YES
    ├─ Fix < 30 min work? YES
    ├─ No architectural change needed? YES
    └─ → RETRY (Code Worker or Test Engineer fix locally)
```

**WHEN TO ESCALATE (Technical Planner):**
```
Issue found
    ├─ Root cause is design decision? YES
    ├─ Affects multiple components? YES
    ├─ Requires ADR or trade-off discussion? YES
    ├─ Test strategy was insufficient? YES
    └─ → ESCALATE (Technical Planner re-assesses)
```

**WHEN TO ESCALATE (Infrastructure):**
```
Issue found
    ├─ Transient after 3x retry? YES
    ├─ Infrastructure-specific (DB, Cache, Network)? YES
    ├─ Outside application code? YES
    └─ → ESCALATE (Infrastructure/Ops team)
```

**WHEN TO ESCALATE (Orchestrator):**
```
Issue found
    ├─ Multiple retries failed? YES
    ├─ Impacts project timeline? YES
    ├─ Needs different execution strategy? YES
    │  └─ (e.g., needed Security Deep instead of standard)
    └─ → ESCALATE (Orchestrator re-plans)
```

---

## Part 8: Re-Planning (When Issues Break Assumptions)

### When Re-Planning is Necessary

```
Issue emerges that violates core Technical Plan assumptions
    ↓
Technical Planner must reassess
    ├─ Was Technical Plan insufficient?
    ├─ Was test strategy wrong?
    ├─ Do we need ADR?
    └─ Do we change approach fundamentally?
```

**Examples:**

| Scenario | Root Cause | Action |
|----------|-----------|--------|
| Performance 10x worse | Assumed O(1), actual O(n) | Optimization ADR + re-implement |
| Third-party API deprecated | API stability not verified | Re-plan integration |
| Security flaw structural | Architectural issue | ADR for new design |
| Concurrent race condition | Spec missed concurrency model | Re-plan with locks/queue |
| Blocked by external team | Dependency not discovered | Orchestrator escalates timeline |

**Re-Plan Flow:**
```
Blocking issue emerges
    ↓
Technical Planner re-assesses
    ├─ Analysis: Why wasn't this caught?
    ├─ Decision: Patch vs. architectural fix?
    └─ Output:
       ├─ Updated Technical Plan (new section)
       ├─ Updated test strategy (if needed)
       ├─ ADR (if applicable)
       └─ Code Worker re-assigned with new context
           └─ + Orchestrator adjusts budget/timeline
```

---

## Part 9: Orchestrator Decision Engine

### How Orchestrator Decides

**Inputs:**
- Technical Assessment from Technical Planner
- Project constraints (budget, timeline, team capacity)
- Risk tolerance

**Outputs:**
```yaml
execution_plan:
  code_worker:
    model: "claude-opus-4"
    capability_level: "standard"  # or simple/complex
    max_tokens: 8000
    iterations: 2

  code_reviewer:
    capability_level: "standard"  # or shallow/deep
    model: "claude-opus-4"

  test_engineer:
    capability_level: "standard"  # or simple/complex
    test_scope: ["unit", "integration", "e2e"]
    e2e_required: true
    regression_required: true

  security_reviewer:
    capability_level: "deep"  # or shallow/standard
    model: "claude-opus-4"

  execution_strategy:
    parallel: true
    timeout_per_task: "1 hour"
    max_retries: 3
    cost_budget: "$50"  # Orchestrator's decision
```

### Decision Heuristics

```
IF complexity=simple AND technical_risk=low:
    → Code Worker: simple, Code Reviewer: shallow, Test: unit only

IF complexity=standard AND technical_risk=medium:
    → Code Worker: standard, Code Reviewer: standard, Test: unit+integration
    
IF complexity=complex AND technical_risk=high:
    → Code Worker: complex, Code Reviewer: deep, Test: unit+integration+e2e+regression
    → Security Reviewer: deep

IF security_surface contains [authentication, sensitive_data]:
    → Security Reviewer: deep (minimum)

IF architecture_impact=high:
    → Code Reviewer: deep, Security Reviewer: deep

IF this is retry after failure:
    → Increase capability_level by 1 step
    → Add more budget/timeout
    → Add extra validation (deeper review, more tests)
```

---

## Part 10: Complete Development Workflow (With All Details)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PLANNING PHASE                                   │
│                                                                              │
│  Technical Planner                                                          │
│  ├─ Input: Approved Spec + Codebase                                       │
│  ├─ Analysis:                                                               │
│  │  ├─ Map to components/services/databases                               │
│  │  ├─ Identify risks and dependencies                                    │
│  │  ├─ Plan test strategy                                                 │
│  │  ├─ Identify security surface                                          │
│  │  └─ Determine if ADR needed                                            │
│  ├─ Output:                                                                 │
│  │  ├─ Technical Plan                                                      │
│  │  ├─ Assessment (complexity, risk, test scope, security surface)        │
│  │  └─ ADR (if needed)                                                    │
│  └──┬─────────────────────────────────────────────────────────────────────┘
│     │
│  Orchestrator                                                               │
│  ├─ Input: Technical Assessment                                           │
│  ├─ Decide:                                                                │
│  │  ├─ Model per role (Sonnet/Opus/Opus-Extended)                        │
│  │  ├─ Capability levels (simple/standard/complex, shallow/standard/deep) │
│  │  ├─ Budget & timeout                                                   │
│  │  ├─ Parallelization strategy                                           │
│  │  └─ Retry policy                                                       │
│  └─ Output: Execution Plan                                                │
│                                                                             │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                           EXECUTION PHASE                                   │
│                      (Parallel with Retry Loops)                           │
│                                                                             │
│  CODE WORKER                                                                │
│  ├─ Generate implementation code                                           │
│  ├─ Create unit tests                                                      │
│  ├─ Local validation (lint, type check, build)                            │
│  │  ├─ Fail? → Retry locally (max 3x)                                    │
│  │  │  └─ Still fail? → Escalate to Code Reviewer                        │
│  │  └─ Pass → continue                                                    │
│  └─ Output: Code + unit tests                                             │
│      │                                                                     │
│      └─────────┬──────────────┐                                           │
│                │              │                                            │
│  CODE REVIEWER │        TEST ENGINEER + TEST RUNNER                       │
│  ├─ Review:   │         ├─ Design test strategy                          │
│  │  ├─ Arch   │         ├─ Implement: unit/integration/E2E/regression   │
│  │  ├─ Logic  │         │                                                │
│  │  ├─ ADR ✓  │         ├─ Run tests:                                    │
│  │  └─ Stds   │         │  ├─ Unit tests                                 │
│  │            │         │  │  ├─ Fail (deterministic)?                 │
│  │ Reject?    │         │  │  │  └─ Send to Code Worker                │
│  │ ├─ Simple  │         │  │  ├─ Fail (transient)?                     │
│  │ │ → Code   │         │  │  │  └─ Retry w/ backoff 3-5x              │
│  │ │   retry  │         │  │  └─ Pass → continue                       │
│  │ │   1-2x   │         │  ├─ Integration tests                        │
│  │ └─ Complex │         │  │  ├─ Infrastructure fail?                  │
│  │   → Tech   │         │  │  │  └─ Retry w/ backoff                   │
│  │   Planner  │         │  │  ├─ Code fail?                            │
│  │            │         │  │  │  └─ Code Worker fix                     │
│  │ Approve?   │         │  │  └─ Pass → continue                       │
│  │ → continue │         │  ├─ E2E tests                                 │
│  │            │         │  │  ├─ Slow? → Code Worker optimize         │
│  │            │         │  │  ├─ Timing? → Test Engineer refine        │
│  │            │         │  │  ├─ Backend? → Code Worker fix             │
│  │            │         │  │  └─ Pass → continue                       │
│  │            │         │  └─ Regression tests                         │
│  │            │         │     ├─ Fail? → Isolate & fix                 │
│  │            │         │     └─ Pass → continue                       │
│  │            │         │                                               │
│  │            │         └─ Output: Test evidence + pass/fail            │
│  │            │                                                          │
│  └────┬───────┴─────────────────────────────────────────────────────────┘
│       │
│       ▼
│  [All tests passed?]
│      ├─ NO → Diagnose & escalate (retry/fix/re-plan)
│      └─ YES → Continue
│             │
│             ▼
│  SECURITY REVIEWER
│  ├─ Analyze code + identified security surface
│  ├─ Depth: shallow/standard/deep (per Orchestrator)
│  ├─ Reject?
│  │  ├─ CRITICAL → STOP. Code Worker immediate fix. Full re-audit.
│  │  ├─ MEDIUM → Conditional approve. Code Worker addresses.
│  │  └─ LOW → Note & merge (prioritize follow-up)
│  └─ Approve → Continue
│      │
│      ▼
│  DOCUMENTATION (if required)
│  ├─ Update: README, API docs, runbooks, architecture docs
│  ├─ Code Worker can write this
│  └─ Output: Documentation
│      │
│      ▼
│  [All Checks Passed?]
│  ├─ YES → PR Ready ✓
│  └─ NO → Escalate to Technical Planner
│          └─ Possible re-plan + re-execute
│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 11: Observability & Metrics

### What to Measure (Per Task)

```
Task
├─ Spec (what was implemented)
├─ Agente (which role)
├─ Model (which LLM)
├─ Capability Level (simple/standard/complex, shallow/standard/deep)
├─ Tokens (input + output)
├─ Cost (model cost)
├─ Latency (time to complete)
├─ Tool Calls (file edits, bash, API calls)
├─ Retries (how many)
├─ Errors (what went wrong)
├─ Escalations (who escalated to whom)
└─ Result (pass/fail/rework)
```

### Key Questions (Data-Driven Optimization)

```
1. COMPLEXITY & EXECUTION
   └─ Does this task really need complex model? Or is standard enough?
   └─ What's the actual cost/token ratio?

2. TESTING STRATEGY
   └─ Is Security Deep finding issues? Or is standard enough?
   └─ Does E2E add value? Or are integration tests sufficient?
   └─ Does regression testing prevent real bugs?

3. PLANNING QUALITY
   └─ How often do we re-plan?
   └─ Root cause of re-plans: insufficient planning or real unpredictability?
   └─ Does deeper Technical Planning reduce rework?

4. RETRY EFFECTIVENESS
   └─ What % of issues are resolved by retry?
   └─ What % need escalation?
   └─ Which issue types are most expensive?

5. MODEL SELECTION
   └─ Which model has best cost/quality ratio per role?
   └─ Does Opus add value over Sonnet for Code Reviewer?
```

### Dashboard Example

```
metrics:
  code_worker:
    avg_tokens: 5200
    avg_cost: $0.12
    retry_rate: 15%  # % of tasks needing retry
    escalation_rate: 3%  # % escalated to Code Reviewer
    success_rate: 82%  # % first-pass approval

  code_reviewer:
    avg_review_time: 12 min
    rejection_rate: 8%
    re_reject_rate: 2%  # % rejected twice
    architectural_issues_found: 3

  test_runner:
    transient_failure_rate: 12%  # resolved by retry
    deterministic_failure_rate: 4%  # logic bug
    flaky_test_rate: 2%
    avg_test_time: 8 min

  security_reviewer:
    vulnerabilities_found: 2
    false_positives: 1
    avg_review_time: 18 min
    critical_issues: 0
```

---

## Part 12: Technology & Implementation

### Phase 1: Pi Agent (Now)
```
Pi Agent
├─ Familiar workflow language
├─ Direct filesystem, git, shell access
├─ Subagent support (Code Worker calls subordinate agents)
└─ Advantages: Fast iteration, low infrastructure
```

### Phase 2: LangGraph (If Needed)
```
LangGraph (only if real need emerges)
├─ Durable execution & checkpointing
├─ Complex state management
├─ Resume after failure
├─ Sophisticated branching
└─ Potential architecture:
   ├─ LangGraph (orchestration + state)
   ├─ Workflow API (abstraction layer)
   └─ Pi Agent (runtime: code execution, subagents)
```

### ADR 01
Decidido começar com LangGraph desde o começo (pi-vs-langgraph.md)

### Observability Stack
```
Day 1: Basic metrics collection
├─ Task telemetry (tokens, cost, latency)
├─ Retry counts
└─ Success/failure tracking

As needed: LangSmith integration
├─ Workflow tracing
├─ Evaluation framework
└─ Cost/performance analysis
```

---

## Part 13: Quick Reference & Checklists

### Spec Workflow Checklist

```
□ Spec Agent produces:
  □ Clear requirement description
  □ Acceptance criteria (testable, specific)
  □ Definition of Done
  □ Identified edge cases

□ Requirements Reviewer validates:
  □ Clarity (anyone can understand)
  □ Completeness (no ambiguity)
  □ Testability (AC is measurable)
  □ Edge cases covered
  □ No impossible requirements

□ Output: Approved Spec ready for development
```

### Technical Planning Checklist

```
□ Technical Planner identifies:
  □ Affected components/services/databases
  □ API changes needed
  □ Schema changes (if any)
  □ Events/messages affected
  □ Dependencies & risks
  
□ Technical Planner assesses:
  □ Complexity level (simple/standard/complex)
  □ Technical risk (low/medium/high)
  □ Architecture impact
  □ Test strategy (what types needed)
  □ Security surface (auth/data/input)
  □ Documentation requirements

□ ADR created? (If architectural decision significant)
  □ Decision documented
  □ Trade-offs explained
  □ Alternatives considered

□ Output: Technical Plan + Assessment + ADR ready for Orchestrator
```

### Orchestrator Decision Checklist

```
□ From Technical Assessment, Orchestrator decides:
  □ Code Worker capability (simple/standard/complex)
  □ Code Worker model (Sonnet/Opus/Opus-Extended)
  □ Code Reviewer capability (shallow/standard/deep)
  □ Test Engineer capability + scope
  □ Security Reviewer capability (shallow/standard/deep)
  □ Budget allocation
  □ Timeout per task
  □ Retry policy (max 3/5/etc)
  □ Parallelization strategy

□ Output: Execution Plan
```

### Code Execution Checklist

```
□ Code Worker:
  □ Generate code per Technical Plan
  □ Create unit tests (>70% coverage)
  □ Local validation (lint, type, build)
  □ If fail → retry locally (max 3x)
  □ Output: Code + tests

□ Code Reviewer:
  □ Validate architecture adherence
  □ Check logic correctness
  □ Verify ADR compliance
  □ Verify coding standards
  □ Approve or provide feedback

□ If rejected:
  □ Simple issue → Code Worker retry (1-2x)
  □ Complex issue → Escalate to Technical Planner

□ Test Engineer + Test Runner:
  □ Design test strategy (unit/integration/E2E/regression)
  □ Implement tests
  □ Execute tests
  □ Capture evidence
  □ Retry on transient failure (backoff strategy)
  
□ If test fails:
  □ Deterministic? → Escalate to Code Worker
  □ Transient? → Retry with backoff
  □ Flaky test? → Test Engineer refine

□ Security Reviewer:
  □ Analyze security surface
  □ Check for vulnerabilities
  □ Assess risk
  □ Critical issue → STOP, immediate fix
  □ Approve or reject

□ Output: Approved code ready for merge
```

### Issue Escalation Quick Reference

| Issue Type | Detection | Action | Escalate To |
|-----------|-----------|--------|-------------|
| Local code error | Code Worker local build | Retry locally (1-3x) | Code Reviewer if persists |
| Logic bug | Code Reviewer or tests | Code Worker fix (1-2x) | Technical Planner if complex |
| Transient test failure | Test Runner | Retry w/ backoff (3-5x) | Infrastructure if persists |
| Deterministic test failure | Test Runner | Code Worker fix logic | Test Engineer if test issue |
| Performance issue | E2E test timeout | Code Worker optimize | Technical Planner if architectural |
| Security vulnerability | Security Reviewer | Code Worker immediate fix | Full re-audit |
| Architectural assumption broken | Any role during execution | Technical Planner re-assess | Orchestrator for re-plan |

---

## Part 14: Example: End-to-End OAuth Implementation

### Specification
```
Request: "Add OAuth Google login to user service"

Spec Agent outputs:
├─ Spec: Google OAuth authentication flow
├─ AC:
│  ├─ User clicks "Login with Google"
│  ├─ OAuth consent screen appears
│  ├─ Browser redirects to callback endpoint
│  ├─ User JWT token issued and stored
│  ├─ Logout clears session
│  └─ Unauthenticated requests get 401
├─ DoD:
│  ├─ Code review passed
│  ├─ Unit tests >80% coverage
│  ├─ Integration tests (auth middleware + database)
│  ├─ E2E browser test (full login flow)
│  ├─ Security deep review (OAuth flow, token storage)
│  ├─ README updated with OAuth setup
│  └─ PR merged
└─ Edge cases:
   ├─ Token expiry during operation
   ├─ Concurrent login attempts
   ├─ Google API unavailable
   └─ Network timeout during token exchange

Requirements Reviewer validates and approves.
```

### Development
```
Technical Planner assesses:
├─ Complexity: standard (OAuth is well-understood pattern)
├─ Technical Risk: medium (integration with Google, token handling)
├─ Architecture Impact: medium (auth middleware affected)
├─ Components affected:
│  ├─ AuthMiddleware (add OAuth check)
│  ├─ UserService (create/update user on Google login)
│  ├─ TokenRepository (store refresh token)
│  └─ AuthEndpoint (callback handler)
├─ Test strategy: unit + integration + E2E + regression
│  └─ E2E: Playwright browser test (Google login flow)
├─ Security surface: {authentication, external_input}
│  └─ Concerns: OAuth token handling, XSS in callback, CSRF
└─ ADR needed? YES
   └─ "Where to store OAuth refresh token?"
      ├─ Decision: PostgreSQL (persistent, associated with user)
      ├─ Trade-off: DB lookup per token refresh
      └─ Alternative considered: Redis (but volatile, adds operational burden)

Orchestrator decides:
├─ Code Worker: standard model, max_tokens 8k, iterations 2
├─ Code Reviewer: standard depth (architecture + logic)
├─ Test Engineer: standard (unit + integration + E2E)
├─ Security Reviewer: deep (OAuth + data handling)
├─ Budget: $50, timeout 2 hours

Code Worker implements:
├─ AuthMiddleware.cs (OAuth validation)
├─ CallbackHandler.cs (token exchange)
├─ TokenRepository.cs (storage)
├─ UserService updates
├─ Unit tests (mocked Google API)
└─ Local validation passes

Code Reviewer validates:
├─ Architecture: ✓ (follows existing pattern)
├─ ADR compliance: ✓ (token stored in DB)
├─ Logic: ✓ (token refresh handled)
└─ Approve

Test Engineer creates tests:
├─ Unit: token refresh, expiry check
├─ Integration: end-to-end flow with mocked Google
├─ E2E: Playwright browser test (actual Google login with test account)
├─ Regression: existing auth endpoints still work

Test Runner executes:
├─ All tests pass (except E2E timeout first attempt)
│  ├─ E2E Retry 1: Playwright timeout (Google slow)
│  ├─ E2E Retry 2: Success
├─ Evidence: Test report, E2E screenshots
└─ Continue

Security Reviewer deep analysis:
├─ OAuth flow: ✓ PKCE used, state verified
├─ Token storage: ✓ encrypted, associated with user
├─ Sensitive data: ✓ not logged
├─ External input: ✓ callback params validated
└─ Approve + note: "Consider implementing token rotation policy (future)"

Documentation updated:
├─ README: Google OAuth setup instructions
├─ API docs: new /auth/google endpoints
└─ Runbook: troubleshooting guide

All checks passed → PR ready ✓
```

---

## Part 15: Final Architecture Diagram

```
                        ┌──────────────────────────────────┐
                        │    SPECIFICATION WORKFLOW        │
                        │  (Sequential: Spec → Validate)   │
                        └────────────────┬─────────────────┘
                                         │
                                  [Approved Spec]
                                         │
        ═════════════════════════════════╪══════════════════════════════════
                                         │
                    ┌────────────────────▼────────────────────┐
                    │       TECHNICAL PLANNING PHASE         │
                    │  Technical Planner + ADR (if needed)   │
                    │  Output: Plan + Assessment + ADR       │
                    └────────────────────┬────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────┐
                    │   ORCHESTRATOR DECISION PHASE          │
                    │  Decide: models, levels, budget        │
                    │  Output: Execution Plan                │
                    └────────────────────┬────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │         EXECUTION PHASE (Parallel with Retry Loops)            │
        │                                                                 │
        │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
        │  │ CODE WORKER  │  │CODE REVIEWER │  │ TEST ENGINEER +      │ │
        │  │              │  │              │  │ TEST RUNNER          │ │
        │  │ • Generate   │  │ • Validate   │  │ • Design tests       │ │
        │  │ • Unit tests │  │ • ADR check  │  │ • Implement tests    │ │
        │  │ • Local      │  │ • Approve or │  │ • Execute (retry w/  │ │
        │  │   validate   │  │   reject     │  │   backoff if needed) │ │
        │  │ • Retry 1-3x │  │ • Retry if   │  │ • Collect evidence   │ │
        │  │   if fail    │  │   simple     │  │ • Diagnose failures  │ │
        │  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
        │         │                 │                      │             │
        │         └─────────────────┼──────────────────────┘             │
        │                           │                                    │
        │                    ┌──────▼─────────┐                          │
        │                    │ All checks ok? │                          │
        │                    ├─ YES: continue │                          │
        │                    └─ NO: escalate  │                          │
        │                    │  (retry/fix/   │                          │
        │                    │   re-plan)     │                          │
        │                    └──────┬─────────┘                          │
        │                           │                                    │
        │                    ┌──────▼──────────────────────┐             │
        │                    │  SECURITY REVIEWER          │             │
        │                    │  • Analyze code             │             │
        │                    │  • Deep level (per exec)    │             │
        │                    │  • Reject if critical       │             │
        │                    │  • Approve or note issues   │             │
        │                    └──────┬──────────────────────┘             │
        │                           │                                    │
        │                    ┌──────▼──────────────────────┐             │
        │                    │  DOCUMENTATION (if needed)  │             │
        │                    │  • Update README, API docs  │             │
        │                    │  • Code Worker can write    │             │
        │                    └──────┬──────────────────────┘             │
        │                           │                                    │
        └───────────────────────────┼────────────────────────────────────┘
                                    │
                            ┌───────▼────────┐
                            │ PR Ready? ✓    │
                            ├─ YES → Merge  │
                            └─ NO → Escalate│
                               (re-plan)    │
                            └────────────────┘
```

---

## Summary: This Factory In One Table

| Phase | Role | Input | Output | Capacity | Retries |
|-------|------|-------|--------|----------|---------|
| **SPEC** | Spec Agent | Request | Spec + AC + DoD | N/A | N/A |
| **SPEC** | Requirements Reviewer | Spec | Approve/Reject | N/A | N/A |
| **PLAN** | Technical Planner | Approved Spec | Plan + Assessment + ADR? | N/A | N/A |
| **PLAN** | Orchestrator | Assessment | Execution Plan | N/A | N/A |
| **EXEC** | Code Worker | Technical Plan | Code + unit tests | simple/standard/complex | 1-3x locally |
| **EXEC** | Code Reviewer | Code | Approve/Reject | shallow/standard/deep | 1-2x if simple |
| **EXEC** | Test Engineer | AC + DoD | Test suite | simple/standard/complex | N/A |
| **EXEC** | Test Runner | Test suite | Evidence + pass/fail | N/A | 3-5x w/ backoff |
| **EXEC** | Security Reviewer | Code | Assessment | shallow/standard/deep | Full re-audit if critical |

---

## Key Takeaways

✅ **9 stable roles** — clarifies responsibility  
✅ **4 capability levels** — flexibility without role explosion  
✅ **Issues are expected** — retry loops + escalation built-in  
✅ **Orchestrator decides execution** — not roles/models ad-hoc  
✅ **ADR condicional** — only when architecturally significant  
✅ **Observability first** — measure to optimize  
✅ **Pi Agent now, LangGraph later** — evolve when needed  
✅ **Re-planning when assumptions break** — not just patching  


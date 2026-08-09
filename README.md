# AI Software Development Factory

Um **agente de desenvolvimento de software autônomo** que transforma uma
solicitação de feature em linguagem natural em um **pull request revisado e
pronto para merge** em um repositório git remoto.

A fábrica é composta por **duas workflows independentes**, unidas por
contrato de versão — e não por acoplamento:

```
┌─────────────────────────┐      spec_version_id      ┌──────────────────────────┐
│  Specification Workflow │ ──── (reference) ───────► │   Development Workflow   │
│  WHAT / WHY             │                           │  HOW / BUILD / PROVE     │
│  request → aproved spec │                           │  aproved spec → PR       │
└─────────────────────────┘                           └──────────────────────────┘
```

## O que ela faz

Com **uma** solicitação de texto, a fábrica:

1. **Spec Workflow** — gera uma especificação aprovada e versionada
   (intent, rationale, acceptance criteria testáveis, definition of done,
   edge cases), com um gate de **aprovação humana**, **sem escrever código**.
2. **Dev Workflow** — recebe a spec **por referência** (`spec_version_id`),
   planeja tecnicamente, decide a execução, implementa, revê, testa,
   verifica segurança e abre o **PR** no host git remoto. Procede
   **autonomamente** até o PR; o humano aprova a spec e faz merge.

Princípio central: **Specification ≠ Execution** — o quê/porquê é
desacoplado do como/execução.

## Características-chave

- **9 papéis estáveis** em duas workflows (Spec Agent, Requirements
  Reviewer, Technical Planner, Orchestrator, Code Worker, Code Reviewer,
  Test Engineer, Test Runner, Security Reviewer).
- **Capability levels** por papel (simple/standard/complex;
  shallow/standard/deep) — intensidade de execução proporcional à
  complexidade, decidida por um **Orchestrator** (camada de decisão pura).
- **Tratamento de issues**: retry com backoff, escalação e **re-planning
  automático**; para para um humano **somente** quando o re-planning falha.
- **ADR condicional**: só para decisões arquiteturais significativas.
- **Resumable**: runs retomam do último checkpoint.
- **Seguro**: credenciais só de env/secret store; código gerado roda em
  **sandbox/container**; secrets redigidos de logs e telemetria.
- **Observável**: telemetria por papel (modelo, nível, tokens, custo,
  latência, retries, erros, escalações, resultado).

## Requisitos

- **Python ≥ 3.14** (gerenciado com `uv`)
- Container runtime (Docker/Podman) para execução sandboxed
- Credenciais LLM e do git host (via ambiente/secret store)
- Acesso a um provedor de modelo de linguagem

## Instalação

```bash
uv sync                # instala dependências e o pacote
uv run ruff check .    # lint
uv run pytest          # testes unit + contract (rede bloqueada)
uv run pytest -m integration   # testes end-to-end (rede + container)
```

## Uso

```bash
# 1. Spec workflow: request → spec aprovada (emite spec_version_id)
echo "Add a password-reset flow to the auth library" | \
  uv run spec-run --request --stdin --format json

# 2. Dev workflow: spec aprovada → PR aberto
uv run dev-run --spec-version-id <id> --format json
```

## Estrutura do projeto

```text
src/ai_factory/
├── shared/            # libs transversais (state, secrets, telemetry, sandbox, git_host, llm, spec_store)
├── spec_workflow/     # StateGraph: spec_agent ↔ requirements_reviewer → aproved spec
├── dev_workflow/      # StateGraph: planner → orchestrator → worker/reviewer/test/security → deliver PR
├── capability_levels/ # mapeamento modelo/orçamento/tool-access por nível
└── cli/               # CLIs finas compondo as bibliotecas (spec-run, dev-run)
tests/
├── unit/              # rede bloqueada
├── contract/          # contrato das barreiras das libs (CLI)
└── integration/       # end-to-end, opt-in
```

Arquitetura **Library-First**: cada papel/capacidade é uma biblioteca
independente testável, exposta por um CLI; as workflows compõem bibliotecas.

## Design & planejamento

Os artefatos de design vivem em `specs/001-ai-dev-factory/`:

| Artefato | Conteúdo |
|----------|----------|
| `spec.md` | Especificação (user stories, requisitos, critérios) |
| `plan.md` | Plano de implementação + constitution check |
| `research.md` | Decisões técnicas (R1–R12: LangGraph, LangSmith, Pydantic, models) |
| `data-model.md` | Modelo de dados (entities, transições, validações) |
| `contracts/` | Contratos de interface (CLI conventions, spec-run, dev-run) |
| `tasks.md` | Tarefas de implementação (T001–T090, por user story) |
| `quickstart.md` | Cenários de validação end-to-end |

## Estado

**Fase atual**: Phase 1 (Setup) concluída — scaffolding do projeto
(pyproject, skeleton do pacote, testes, AGENTS.md, lint/test config).
**Próximo**: Phase 2 (Foundation — modelos de estado, secrets, spec-store,
abstração LLM, convenção CLI).

Consulte `AGENTS.md` para as convenções para agentes de IA e as diretrizes
da constituição (Library-First, Test-First, CLI).

## Roadmap (por user story)

1. **US1 (P1)** Spec Workflow end-to-end — *MVP*
2. **US2 (P1)** Dev Workflow end-to-end + entrega de PR
3. **US3 (P1)** Issue handling (retry/escalation/re-plan)
4. **US4 (P2)** Capability levels + Orchestrator
5. **US5 (P2)** Observabilidade & telemetria
6. **US6 (P3)** ADRs condicionais

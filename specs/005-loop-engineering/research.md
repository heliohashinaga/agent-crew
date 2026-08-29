# Research: Loop Engineering (Arquitetura, Estado Atual e Visão)

**Feature**: `005-loop-engineering` | **Data**: 2026-08-15
**Status**: **PLANNED** (decisão A fechada — ver §6).

---

## Contexto

O usuário quer desenvolver **loop engineering** para o ai-dev-factory: uma
camada de controle autônomo que executa trabalho, verifica por um gate externo,
repara falhas e itera até sucesso ou terminação — com estado durável (spine) e
escalação a humano. Este documento registra a conversa para retomada futura.

## 1. Definição de Loop Engineering (pesquisa)

**Loop engineering** = projetar loops de controle automatizados para agentes de
IA: `executar → verificar → reparar → repetir` até um objetivo verificável,
com intervenção humana mínima. Complementa (não substitui) prompt engineering.

**Peças centrais de todo loop:**
1. **Trigger** — início: manual (CLI), tempo (scheduled), evento (webhook).
2. **Ator (actor)** — o agente/trabalho que executa a iteração (seam trocável).
3. **Gate / Oracle** — verificação **externa e independente** (testes, linter,
   reviewer separado). Invariante: **o ator nunca avalia o próprio trabalho**
   (no self-grading).
4. **Repair path** — feedback das falhas (gate reasons) devolvido ao ator para
   a próxima iteração, de forma **concisa** (nunca dump).
5. **Terminação** — limites duros (max iter, tokens, tempo, custo) + **ratchet
   de progresso** (para se iterações não avançam). Sem isso: loop infinito /
   orçamento infinito.
6. **Spine / Ledger** — estado durável do loop (iterações, vereditos, budget,
   run_id) → resume e auditoria.

**Dois sentidos do termo:** (a) IA/agentes (relevante aqui — IBM, O'Reilly,
Anthropic, Pragmatic Engineer, freeCodeCamp); (b) industrial = controls
engineering com PLCs (só o nome coincide).

## 2. Estado atual: o dev_workflow é um fluxo, não um loop engineering

Analisado `src/ai_factory/dev_workflow/graph.py` (StateGraph do LangGraph,
`build_dev_graph`):

```
START → load_spec → planner → orchestrator → code_worker → code_reviewer
      → test_engineer → test_runner(sandbox) → security_reviewer → deliver(PR) → END
      └─ fail / stop_human → END
```

**É um pipeline single-run com loops internos limitados** (constantes
`MAX_REWORK = 2`, `MAX_REPLAN = 2`):

- Rework loop: `code_reviewer`/`test_runner` falham → `rework` → `code_worker`
  (bump de capability por tentativa, FR-015).
- Issue handling (US3): `handle_failure` classifica a falha → `retry_backoff`
  (transiente, backoff exponencial registrado p/ observabilidade) →
  `security_fix` (CRITICAL: fix imediato + re-audit) → `replan` (auto replan,
  ≤ `MAX_REPLAN`) → `stop_human` (escala a humano, exit 5).
- Checkpoints por fase (`CheckpointStore` + `resume=True`): run interrompido
  retoma pulando fases completas.
- Budget **soft** (FR-019): overspend é sinalizado, nunca aborta.

**O que falta vs. loop engineering** (ver spec.md para detalhes):
- Loop externo que re-executa o ator até um gate externo passar.
- Gate/oracle reutilizável de primeira classe (os gates hoje são nodes internos).
- Ledger/spine em nível de loop (hoje: checkpointer por-fase dentro do run).
- `max_iterations`/budget/ratchet em nível de loop + escalação com resumo.
- Interface de ator genérica.

## 3. Arquitetura de referência de loop engineering (4 camadas)

```
CAMADA 4 · Observabilidade & Integração
  telemetry (role, tokens, cost, latency) | CLI | MCP/connectors | skills

CAMADA 3 · Composição / Orquestração
  handoff entre loops | locks | worktrees git paralelos | subagentes

CAMADA 2 · Runtime & Estado
  trigger/scheduler | spine (ledger durável) | budget tracker
  | context manager | escalação a humano

CAMADA 1 · Núcleo de controle
  ator → gate (oráculo externo) → repair → terminação
```

**Spine (coração da arquitetura)** — registro append-only por run:

```
run_id | status (running/passed/exhausted/stalled/error)
config: {actor, gate, max_iterations, budget, ratchet}
iterations: [{n, actor_out, gate:{passed, checks}, budget} ...]
final: {status, iterations, budget, pr/artifact refs}
```

Implementações possíveis do spine: arquivo (memory.md/JSON), SQLite, S3.
**O `memory.md` proposto pelo usuário É o spine.**

**Composição entre loops (Camada 3):**
- A) Sequencial/handoff: loops por fase que se passam o bastão via spine.
- B) Aninhado (nested): loop externo contendo micro-loops internos — como o
  dev_workflow já faz com MAX_REWORK/MAX_REPLAN.
- C) Paralelo: supervisor despacha worktrees + subagentes (explorer/implementer/
  verifier).

**Regras de coordenação obrigatórias:**
1. **State-gating sobre time-trigger**: o schedule acorda o loop; o spine
   decide se ele pode agir (fase anterior concluída). Idempotência obrigatória.
2. **Single-writer por seção**: cada loop é dono da sua parte do spine;
   paralelismo real só com worktrees/arquivos isolados.
3. **Escrita atômica** (tmp + rename): leitor nunca vê registro pela metade.
4. **Budget por nível E global**: N loops × sem limite = orçamento explodindo.
5. **memory.md estruturado e bounded**: JSON machine-readable + human-readable,
   rotativo (resumo das últimas N iterações + refs, nunca histórico infinito).

## 4. Visão multi-loop do usuário (futuro / arquitetura-alvo)

```
plan-loop → code-loop → review-loop → qa-loop → security-loop
  (cada um acorda por trigger de tempo, lê o spine, age se state-gated,
   escreve resultado de volta)

Nível 1 (micro-loops por role): code-loop (ator=code, gate=test+review),
  review-loop (conceitualmente: ator=code, gate=reviewer — review é gate,
  não ator), etc. — **já existem** internamente no dev_workflow hoje.
Nível 2 (loop externo): iteração = pipeline inteiro como ator; gate externo
  (suite determinística + reviewer independente) sobre o resultado global.
```

Aviso de engenharia: cada nível de loop aninhado **multiplica custo de
tokens/contexto** — pocos níveis, limites apertados; budget e ratchet em cada
nível.

## 5. Decisões fechadas no spec (Clarifications, 2026-08-15)

- **Q1 = A**: interface de ator genérica + 1 binding concreto = pipeline da
  factory (spec folder aprovado → execução → PR). Futuros atores (vídeo,
  tarefas arbitrárias) plugam sem mudar o núcleo.
- **Q2 = C**: gate em 2 estágios — (a) verificações determinísticas
  (network-free, passam primeiro); (b) reviewer independente (role/modelo
  separado, integration-gated).
- **Q3 = A**: sem aprovações interativas; humanos via escalação na terminação
  + start/resume manual via CLI.

## 6. Decisão de escopo v1 — fechada: Opção A

**Decisão: Opção A.** manter v1 como **harness único** com ator genérico +
1 binding concreto (pipeline folder-driven da factory), trigger manual, e
ledger/spine de **arquivo JSON-lines** (o `memory.md` do usuário). A visão
multi-loop (plan-loop → code-loop → review-loop → qa-loop → security-loop,
triggers de tempo, worktrees/subagentes paralelos) fica **registrada como
arquitetura-alvo**, fora do escopo de v1.

**Rationale**: escopo contido e testável; atende ao pedido central do usuário
(um loop autônomo verificável e terminável com estado durável) sem entregar
a máquina multi-loop de uma vez. A engine é **reutilizável**: SLAs, triggers
e composição multi-loop plugam depois sem mudar o núcleo (o binding concreto
substituível). Alinha com a constituição (YAGNI, Simplicidade) e com o padrão
`researcher` (biblioteca Library-First, CLI, telemetria, testável sem rede).

**Alternativas consideradas**:
- **Opção B** (loop-por-fase + memory.md + triggers de tempo): maior escopo,
  custo de contexto multiplicado por loop (research §4 aviso), foge do core
  ask. **Rejeitada para v1**; registrada como arquitetura-alvo/futuro.
- **Nenhuma engine, duplicar gates no dev_workflow**: não atende ao pedido e
  viola Library-First (FR-010). **Rejeitada.**

## 7. Decisões de design consolidadas (para plan.md / data-model.md)

| # | Decisão | Justificativa / fonte |
|---|---------|-----------------------|
| D1 | v1 = harness único, **sem LangGraph** — loop de controle direto sobre seams `Actor`/`Gate` (não um grafo) | núcleo simples, determinístico, testável sem rede |
| D2 | **Ledger = arquivo JSON-lines** (tmp+rename = escrita atômica; `run_id`-scoped; resume exige mesmo `run_id`) | resume durável, testável em `tmp_path` |
| D3 | **Gate em 2 estágios** (Q2=C): determinística primeiro, reviewer independente depois (integration-gated) | invariante no self-grading |
| D4 | **Ator genérico + 1 binding concreto** (pipeline folder-driven da factory como seam, não wireado em nodes) | Q1=A, FR-012 |
| D5 | **Terminação** = `max_iterations` (obrigatório, >0) + budget opcional (time/tokens/cost) + ratchet de stall | segurança (US3), FR-003/FR-009 |
| D6 | **Escalação** na terminação = resumo conciso (status, iterações, vereditos bounded, budget, refs artifacts) | FR-004, Q3=A |
| D7 | Telemetria por iteração `role == "loop_engine"` via seam `shared/telemetry` + `shared/cli_util` | FR-008, Principle V |
| D8 | Reuso de `shared/cli_util.py` (JSON/human, exit codes, redação) — exit `0` passed / `2` exhausted/escalation/stalled / `3` resolution-config / `4` error / `1` usage | Principle II, FR-007 |
| D9 | **Não wirear** loop_engine em nodes do dev_workflow (v1) | FR-010 (Library-First) |

## Fontes (pesquisa web 2026)

IBM — What Is Loop Engineering? · O'Reilly Radar — Loop Engineering ·
Anthropic/Claude — Getting started with loops · Pragmatic Engineer — What is
loop engineering? · freeCodeCamp — Prompt vs Loop Engineering ·
AddyOsmani — Loop Engineering · aipatternbook — Loop Engineering.
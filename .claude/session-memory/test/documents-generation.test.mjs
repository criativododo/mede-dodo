import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tempDirectory } from './helpers.mjs';
import {
  archiveExcessJournals,
  deriveState,
  listJournals,
  projectPaths,
  regenerateExecutiveSummary,
  renderExecutiveSummary,
  withMarker,
} from '../lib/documents.mjs';

const PROJECT = 'projeto-teste';

function fakeJournal(relativePath, meta) {
  return { filePath: relativePath, relativePath, content: '', meta };
}

function writeJournalFile(memoryPath, projectId, relativeName, meta) {
  const filePath = join(projectPaths(memoryPath, projectId).journals, relativeName);
  mkdirSync(join(filePath, '..'), { recursive: true });
  const content = [`# Journal — ${meta.objective}`, '', withMarker('', meta).trimEnd(), ''].join('\n');
  writeFileSync(filePath, content, 'utf8');
  return filePath;
}

// 1. Geração inicial ---------------------------------------------------------

test('geração inicial: zero journals produz estado vazio determinístico', () => {
  const state = deriveState([], PROJECT);
  assert.equal(state.project, PROJECT);
  assert.equal(state.phase, 'Nenhuma sessão registrada ainda.');
  assert.equal(state.sprint, 'Não formalizada');
  assert.equal(state.lastJournal, null);
  assert.equal(state.lastCommit, null);
  assert.equal(state.lastAdr, null);
  assert.deepEqual(state.blockers, []);
  assert.equal(state.summary, 'Nenhuma sessão registrada ainda.');

  const summary = renderExecutiveSummary([], PROJECT);
  assert.match(summary, /Nenhuma sessão registrada ainda\./);
});

// 2. Múltiplos journals -------------------------------------------------------

test('múltiplos journals: estado deriva sempre do journal de endedAt mais recente', () => {
  const older = fakeJournal('projects/x/journals/2026/07/a.md', {
    endedAt: '2026-07-01T10:00:00.000Z', phase: 'Fase A', sprint: 'S1',
    blockers: ['bloqueio antigo'], nextTask: 'tarefa antiga', source: { head: 'aaa1111' },
  });
  const newer = fakeJournal('projects/x/journals/2026/08/b.md', {
    endedAt: '2026-08-01T10:00:00.000Z', phase: 'Fase B', sprint: 'S2',
    blockers: [], nextTask: 'tarefa nova', source: { head: 'bbb2222' },
  });
  const state = deriveState([older, newer], PROJECT);
  assert.equal(state.phase, 'Fase B');
  assert.equal(state.sprint, 'S2');
  assert.equal(state.nextTask, 'tarefa nova');
  assert.deepEqual(state.blockers, []);
  assert.equal(state.lastJournal, 'projects/x/journals/2026/08/b.md');
  assert.equal(state.lastCommit, 'bbb2222');

  // ordem de entrada não deve importar
  const stateReversed = deriveState([newer, older], PROJECT);
  assert.deepEqual(state, stateReversed);
});

test('carry-forward: lastAdr e summary usam o journal ativo mais recente que os declara, não necessariamente o último', () => {
  const withAdr = fakeJournal('projects/x/journals/2026/07/a.md', {
    endedAt: '2026-07-01T10:00:00.000Z', phase: 'Fase A', sprint: 'S1',
    adrsAffected: ['ADR-018 — Memória operacional'], summary: 'Resumo antigo.', source: { head: 'aaa1111' },
  });
  const withoutAdr = fakeJournal('projects/x/journals/2026/08/b.md', {
    endedAt: '2026-08-01T10:00:00.000Z', phase: 'Fase B', sprint: 'S2',
    adrsAffected: [], summary: null, source: { head: 'bbb2222' },
  });
  const state = deriveState([withAdr, withoutAdr], PROJECT);
  assert.equal(state.phase, 'Fase B');
  assert.equal(state.lastAdr, 'ADR-018');
  assert.equal(state.summary, 'Resumo antigo.');
});

// 3. Regeneração completa -------------------------------------------------------

test('regeneração completa: cada chamada reescreve o executive-summary do zero, sem herdar conteúdo manual anterior', () => {
  const dir = tempDirectory();
  try {
    mkdirSync(projectPaths(dir, PROJECT).root, { recursive: true });
    writeFileSync(projectPaths(dir, PROJECT).executiveSummary, 'LIXO MANUAL QUE NÃO DEVE SOBREVIVER À REGENERAÇÃO');
    writeJournalFile(dir, PROJECT, '2026/08/2026-08-01_1000.md', {
      endedAt: '2026-08-01T10:00:00.000Z', objective: 'Sessão real', phase: 'Fase Teste', sprint: 'S1',
      blockers: [], nextTask: 'Próxima tarefa real', source: { head: 'cafe123' },
    });
    regenerateExecutiveSummary(dir, PROJECT);
    const summary = readFileSync(projectPaths(dir, PROJECT).executiveSummary, 'utf8');
    assert.equal(summary.includes('LIXO MANUAL'), false);
    assert.match(summary, /Fase Teste/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

// 4. Idempotência ---------------------------------------------------------------

test('idempotência: regenerar duas vezes seguidas com os mesmos journals produz arquivo byte-idêntico', () => {
  const dir = tempDirectory();
  try {
    writeJournalFile(dir, PROJECT, '2026/08/2026-08-01_1000.md', {
      endedAt: '2026-08-01T10:00:00.000Z', objective: 'Sessão A', phase: 'Fase X', sprint: 'S1',
      blockers: ['bloqueio'], nextTask: 'tarefa', adrsAffected: ['ADR-021 — teste'], summary: 'resumo', source: { head: 'aaaa111' },
    });
    writeJournalFile(dir, PROJECT, '2026/08/2026-08-02_1100.md', {
      endedAt: '2026-08-02T11:00:00.000Z', objective: 'Sessão B', phase: 'Fase Y', sprint: 'S2',
      blockers: [], nextTask: 'próxima', source: { head: 'bbbb222' },
    });

    regenerateExecutiveSummary(dir, PROJECT);
    const first = readFileSync(projectPaths(dir, PROJECT).executiveSummary, 'utf8');
    regenerateExecutiveSummary(dir, PROJECT);
    const second = readFileSync(projectPaths(dir, PROJECT).executiveSummary, 'utf8');
    assert.equal(first, second);

    const journalsA = listJournals(dir, PROJECT);
    const journalsB = listJournals(dir, PROJECT);
    assert.equal(renderExecutiveSummary(journalsA, PROJECT), renderExecutiveSummary(journalsB, PROJECT));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('determinismo: dois conjuntos idênticos de journals (ordens de entrada diferentes) produzem o mesmo executive-summary', () => {
  const j1 = fakeJournal('projects/x/journals/2026/08/a.md', { endedAt: '2026-08-01T10:00:00.000Z', objective: 'A', phase: 'Fase 1', sprint: 'S1', blockers: ['x'], nextTask: 'y', source: { head: 'aaa' } });
  const j2 = fakeJournal('projects/x/journals/2026/08/b.md', { endedAt: '2026-08-02T10:00:00.000Z', objective: 'B', phase: 'Fase 2', sprint: 'S2', blockers: [], nextTask: 'z', source: { head: 'bbb' } });
  const j3 = fakeJournal('projects/x/journals/2026/08/c.md', { endedAt: '2026-08-03T10:00:00.000Z', objective: 'C', phase: 'Fase 3', sprint: 'S3', blockers: [], nextTask: 'w', source: { head: 'ccc' } });

  const permutations = [[j1, j2, j3], [j3, j2, j1], [j2, j1, j3], [j2, j3, j1]];
  const outputs = permutations.map((set) => renderExecutiveSummary(set, PROJECT));
  assert.equal(new Set(outputs).size, 1);
});

// 5. Arquivamento (item 3 do pedido) ---------------------------------------------

test('arquivamento: janela ativa acima do limite consolida os journals mais antigos em archive/YYYY-MM.md', () => {
  const dir = tempDirectory();
  try {
    for (let index = 1; index <= 7; index += 1) {
      const endedAt = `2026-0${Math.min(index, 9)}-01T10:00:00.000Z`;
      writeJournalFile(dir, PROJECT, `2026/0${index}/2026-0${index}-01_1000.md`, {
        endedAt, objective: `Sessão ${index}`, phase: `Fase ${index}`, sprint: 'S1', blockers: [], nextTask: 'tarefa', source: { head: `commit${index}` },
      });
    }
    assert.equal(listJournals(dir, PROJECT).length, 7);
    const result = archiveExcessJournals(dir, PROJECT, 5);
    assert.equal(result.archived.length, 2);
    assert.equal(listJournals(dir, PROJECT).length, 5, 'apenas os 5 mais recentes permanecem ativos');

    // as duas sessões mais antigas (1 e 2) foram consolidadas, não perdidas
    const archiveFiles = ['2026-01.md', '2026-02.md'].map((name) => join(projectPaths(dir, PROJECT).archive, name));
    const consolidated = archiveFiles.filter((filePath) => existsSync(filePath)).map((filePath) => readFileSync(filePath, 'utf8')).join('\n');
    assert.match(consolidated, /Sessão 1/);
    assert.match(consolidated, /Sessão 2/);
    assert.equal(consolidated.includes('Sessão 7'), false, 'journal ativo não deve estar no archive');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('arquivamento: idempotente quando o total já está dentro do limite', () => {
  const dir = tempDirectory();
  try {
    writeJournalFile(dir, PROJECT, '2026/08/2026-08-01_1000.md', {
      endedAt: '2026-08-01T10:00:00.000Z', objective: 'Única', phase: 'Fase', sprint: 'S1', blockers: [], nextTask: 'tarefa', source: { head: 'aaa' },
    });
    const result = archiveExcessJournals(dir, PROJECT, 5);
    assert.deepEqual(result.archived, []);
    assert.equal(listJournals(dir, PROJECT).length, 1);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

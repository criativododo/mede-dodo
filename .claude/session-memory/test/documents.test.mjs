import test from 'node:test';
import assert from 'node:assert/strict';
import { rmSync, writeFileSync } from 'node:fs';
import { tempDirectory } from './helpers.mjs';
import { createInitialMemory } from '../lib/scaffold.mjs';
import { REQUIRED_JOURNAL_HEADINGS, listJournals, nextJournalPath, regenerateExecutiveSummary, validateMemory, withMarker } from '../lib/documents.mjs';

function journalContent(meta) {
  return [
    '# Journal — Fixture', '',
    withMarker('', meta).trim(), '',
    ...REQUIRED_JOURNAL_HEADINGS.flatMap((heading) => [`## ${heading}`, '', '- Fixture', '']),
  ].join('\n');
}

test('inicializa a estrutura canônica e valida journals obrigatórios de um projeto', () => {
  const directory = tempDirectory();
  try {
    createInitialMemory(directory);
    assert.equal(validateMemory(directory).valid, true);
    const journalPath = nextJournalPath(directory, 'meu-projeto', '2026-07-30T12:00:00.000Z', 'nonce1');
    writeFileSync(journalPath, journalContent({ endedAt: '2026-07-30T12:00:00.000Z', objective: 'Fixture', phase: 'Fase 4', sprint: 'S1', source: { head: 'abcdef0' } }));
    regenerateExecutiveSummary(directory, 'meu-projeto');
    const validation = validateMemory(directory, 'meu-projeto');
    assert.equal(validation.valid, true, validation.errors.join('\n'));
    assert.equal(validation.journals.length, 1);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('isolamento por projeto: journals de um projeto não aparecem em outro nem no resumo alheio', () => {
  const directory = tempDirectory();
  try {
    createInitialMemory(directory);
    const pathA = nextJournalPath(directory, 'projeto-a', '2026-08-01T10:00:00.000Z', 'a1');
    writeFileSync(pathA, journalContent({ endedAt: '2026-08-01T10:00:00.000Z', objective: 'Trabalho A', phase: 'Fase A', sprint: 'S1', source: { head: 'aaa1111' } }));
    regenerateExecutiveSummary(directory, 'projeto-a');

    const pathB = nextJournalPath(directory, 'projeto-b', '2026-08-02T10:00:00.000Z', 'b1');
    writeFileSync(pathB, journalContent({ endedAt: '2026-08-02T10:00:00.000Z', objective: 'Trabalho B', phase: 'Fase B', sprint: 'S2', source: { head: 'bbb2222' } }));
    regenerateExecutiveSummary(directory, 'projeto-b');

    assert.equal(listJournals(directory, 'projeto-a').length, 1);
    assert.equal(listJournals(directory, 'projeto-b').length, 1);
    assert.equal(listJournals(directory, 'projeto-a')[0].meta.objective, 'Trabalho A');
    assert.equal(listJournals(directory, 'projeto-b')[0].meta.objective, 'Trabalho B');

    const validationA = validateMemory(directory, 'projeto-a');
    assert.equal(validationA.journals.length, 1);
    assert.equal(validationA.journals[0].meta.objective, 'Trabalho A');
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

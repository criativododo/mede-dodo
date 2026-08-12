import { existsSync, readdirSync, readFileSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { atomicWrite, dateParts, relativePosix, fail } from './core.mjs';

export const REQUIRED_JOURNAL_HEADINGS = [
  'Objetivo', 'Contexto', 'Trabalhos realizados', 'Arquivos alterados', 'Arquivos criados',
  'Arquivos removidos', 'Commits', 'Testes', 'Decisões', 'ADRs afetadas',
  'Problemas encontrados', 'Bloqueios', 'Próxima tarefa', 'Observações', 'Confiança da IA',
];

const MARKER_START = '<!-- session-memory';
const MARKER_END = '-->';

export function withMarker(value, data) {
  return `${MARKER_START}\n${JSON.stringify(data, null, 2)}\n${MARKER_END}\n\n${value}`;
}

export function readMarker(value, label = 'documento') {
  const start = value.indexOf(MARKER_START);
  const end = value.indexOf(MARKER_END, start);
  if (start === -1 || end === -1) fail(`Metadados session-memory ausentes em ${label}.`);
  const raw = value.slice(start + MARKER_START.length, end).trim();
  try {
    return JSON.parse(raw);
  } catch (error) {
    fail(`Metadados inválidos em ${label}: ${error.message}`);
  }
}

/**
 * Cada projeto vive isolado sob `projects/<projectId>/` no repositório de memória
 * (hub compartilhado por todos os projetos, um clone só). Nenhuma sessão lê ou escreve
 * fora da pasta do seu próprio `projectId` — é o que garante que trabalho em um
 * repositório nunca vaze para o resumo executivo de outro.
 */
export function projectPaths(memoryPath, projectId) {
  const root = join(memoryPath, 'projects', projectId);
  return {
    root,
    journals: join(root, 'journals'),
    archive: join(root, 'archive'),
    executiveSummary: join(root, 'executive-summary.md'),
    driveState: join(root, 'drive-sync-state.json'),
  };
}

/**
 * Ordena journals por recência (endedAt decrescente) com desempate determinístico por
 * relativePath (ADR-021, Fase 2, critério 1/2): dois conjuntos idênticos de journals devem
 * sempre produzir a mesma ordem, mesmo quando dois journals têm o mesmo endedAt e mesmo que
 * a ordem de leitura do sistema de arquivos varie entre chamadas ou sistemas operacionais.
 */
export function sortJournalsByRecency(journals) {
  return [...journals].sort((a, b) =>
    String(b.meta.endedAt ?? '').localeCompare(String(a.meta.endedAt ?? ''))
    || a.relativePath.localeCompare(b.relativePath));
}

function readJournalsUnder(memoryPath, journalsRoot) {
  if (!existsSync(journalsRoot)) return [];
  const found = [];
  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const entryPath = join(directory, entry.name);
      if (entry.isDirectory()) visit(entryPath);
      else if (entry.isFile() && entry.name.endsWith('.md')) found.push(entryPath);
    }
  }
  visit(journalsRoot);
  const journals = found.map((filePath) => {
    const content = readFileSync(filePath, 'utf8');
    return { filePath, relativePath: relativePosix(memoryPath, filePath), content, meta: readMarker(content, filePath) };
  });
  return sortJournalsByRecency(journals);
}

/** Journals ativos (não arquivados) do projeto informado, mais recentes primeiro. */
export function listJournals(memoryPath, projectId) {
  return readJournalsUnder(memoryPath, projectPaths(memoryPath, projectId).journals);
}

/**
 * Nome do journal inclui um nonce curto de publicação: cada
 * sessão trabalha em seu próprio worktree isolado, sem visibilidade sobre journals que
 * outras sessões concorrentes ainda não publicaram — um `existsSync` local não basta para
 * evitar colisão de nome entre duas sessões terminando no mesmo minuto. Incluir o session
 * nonce torna o nome único por construção, sem depender de detectar a colisão.
 */
function publicationSuffix(publicationNonce) {
  if (!publicationNonce) return '';
  const safe = String(publicationNonce).replace(/[^a-zA-Z0-9]/g, '').slice(0, 8);
  return safe ? `--${safe}` : '';
}

export function nextJournalPath(memoryPath, projectId, endedAt, publicationNonce) {
  const parts = dateParts(endedAt);
  const directory = join(projectPaths(memoryPath, projectId).journals, parts.year, parts.month);
  mkdirSync(directory, { recursive: true });
  const base = `${parts.localDate}_${parts.hhmm}${publicationSuffix(publicationNonce)}`;
  let attempt = 1;
  let candidate = join(directory, `${base}.md`);
  while (existsSync(candidate)) {
    attempt += 1;
    candidate = join(directory, `${base}-${String(attempt).padStart(2, '0')}.md`);
  }
  return candidate;
}

/**
 * Deriva o estado "atual" inteiramente a partir do conjunto de journals ATIVOS do projeto —
 * função pura, sem I/O (ADR-021, Fase 2, critério 3): nenhum campo aqui pode vir de um
 * arquivo derivado previamente escrito. Journals idênticos (em qualquer ordem de entrada)
 * sempre produzem o mesmo resultado.
 *
 * `blockers`/`nextTask`/`phase`/`sprint` vêm sempre do journal mais recente (cada `/fim`
 * declara o estado corrente por completo, nunca acumula). `lastAdr`/`summary` usam
 * "carry-forward": se o journal mais recente não menciona ADR ou não traz resumo, busca-se
 * o journal mais recente que traga, para não perder informação que uma sessão anterior já
 * havia declarado. O horizonte desse carry-forward é o conjunto de journals ainda ativos
 * (não arquivados) — uma vez que um journal é consolidado em `archive/YYYY-MM.md` (ADR-030),
 * o valor que ele carregava só permanece disponível se já tiver sido capturado no
 * `executive-summary.md` gerado antes do arquivamento.
 */
export function deriveState(journals, projectId) {
  const sorted = sortJournalsByRecency(journals);
  const latest = sorted[0];
  const withAdr = sorted.find((journal) => journal.meta.adrsAffected?.length);
  const lastAdr = withAdr ? (withAdr.meta.adrsAffected.at(-1).match(/ADR-\d+/)?.[0] ?? null) : null;
  const withSummary = sorted.find((journal) => journal.meta.summary);
  return {
    schemaVersion: 1,
    project: projectId,
    updatedAt: latest?.meta.endedAt ?? null,
    phase: latest?.meta.phase ?? 'Nenhuma sessão registrada ainda.',
    sprint: latest?.meta.sprint ?? 'Não formalizada',
    lastJournal: latest?.relativePath ?? null,
    lastCommit: latest?.meta.source?.head ?? null,
    lastAdr,
    blockers: latest?.meta.blockers ?? [],
    nextTask: latest?.meta.nextTask ?? 'Nenhuma sessão registrada ainda — execute /inicio e /fim para começar.',
    summary: withSummary?.meta.summary ?? 'Nenhuma sessão registrada ainda.',
  };
}

/** Um único documento gerado por projeto — substitui PROJECT_STATUS.md + START_HERE_NEXT_SESSION.md. */
export function renderExecutiveSummary(journals, projectId) {
  const status = deriveState(journals, projectId);
  const blockersBlock = status.blockers.length ? status.blockers.map((item) => `- ${item}`).join('\n') : '- Nenhum bloqueio informado.';
  return withMarker(`# Resumo executivo — ${status.project}\n\n> Gerado pelo Session Memory a partir dos journals ativos deste projeto. Não editar manualmente.\n\n- **Projeto:** ${status.project}\n- **Fase:** ${status.phase}\n- **Sprint:** ${status.sprint}\n- **Último journal:** ${status.lastJournal ?? 'Nenhum'}\n- **Último commit relevante:** ${status.lastCommit ? status.lastCommit.slice(0, 7) : 'Não informado'}\n- **Última ADR:** ${status.lastAdr ?? 'Não informada'}\n\n## Resumo\n\n${status.summary}\n\n## Bloqueios\n\n${blockersBlock}\n\n## Próxima tarefa\n\n${status.nextTask}\n`, status);
}

/**
 * Único ponto de escrita do artefato gerado do projeto (`executive-summary.md`). Sempre relê
 * o conjunto de journals ativos do disco e regenera do zero — nunca faz patch incremental
 * sobre o conteúdo anterior, o que torna a regeneração idempotente por construção.
 */
export function regenerateExecutiveSummary(memoryPath, projectId) {
  const journals = listJournals(memoryPath, projectId);
  atomicWrite(projectPaths(memoryPath, projectId).executiveSummary, renderExecutiveSummary(journals, projectId));
  return deriveState(journals, projectId);
}

function monthKey(endedAt) {
  const parts = dateParts(endedAt);
  return `${parts.year}-${parts.month}`;
}

/**
 * Consolida journals excedentes em `archive/YYYY-MM.md` do projeto (item 3 do pedido).
 * Mantém sempre os `keep` journals mais recentes ativos em `journals/`; os demais são
 * anexados ao arquivo mensal correspondente (append-only — arquivos de archive nunca são
 * regenerados, apenas recebem novas entradas) e removidos de `journals/`. Idempotente: se
 * o total já está dentro do limite, não faz nada.
 */
export function archiveExcessJournals(memoryPath, projectId, keep = 5) {
  const paths = projectPaths(memoryPath, projectId);
  const journals = listJournals(memoryPath, projectId);
  if (journals.length <= keep) return { archived: [] };

  const toArchive = journals.slice(keep);
  const byMonth = new Map();
  for (const journal of toArchive) {
    const key = monthKey(journal.meta.endedAt);
    if (!byMonth.has(key)) byMonth.set(key, []);
    byMonth.get(key).push(journal);
  }

  for (const [key, entries] of byMonth) {
    const archivePath = join(paths.archive, `${key}.md`);
    mkdirSync(paths.archive, { recursive: true });
    const existing = existsSync(archivePath) ? readFileSync(archivePath, 'utf8') : `# Journals arquivados — ${key}\n`;
    const appended = [existing.trimEnd(), '', ...entries.map((entry) => entry.content.trimEnd())].join('\n\n');
    atomicWrite(archivePath, `${appended}\n`);
  }

  for (const journal of toArchive) rmSync(journal.filePath, { force: true });
  return { archived: toArchive.map((journal) => journal.relativePath) };
}

export function validateMemory(memoryPath, projectId) {
  const errors = [];
  if (!existsSync(join(memoryPath, 'README.md'))) errors.push('Ausente: README.md');
  if (!projectId) return { valid: errors.length === 0, errors, journals: [] };

  const paths = projectPaths(memoryPath, projectId);
  if (!existsSync(paths.executiveSummary)) errors.push(`Ausente: ${relativePosix(memoryPath, paths.executiveSummary)}`);
  const journals = listJournals(memoryPath, projectId);
  for (const journal of journals) {
    for (const heading of REQUIRED_JOURNAL_HEADINGS) {
      if (!journal.content.includes(`## ${heading}`)) errors.push(`${journal.relativePath}: seção "${heading}" ausente`);
    }
  }
  if (existsSync(paths.executiveSummary)) {
    try { readMarker(readFileSync(paths.executiveSummary, 'utf8'), relativePosix(memoryPath, paths.executiveSummary)); } catch (error) { errors.push(error.message); }
  }
  return { valid: errors.length === 0, errors, journals };
}

export function journalSection(title, lines) {
  const content = Array.isArray(lines) ? lines : [lines];
  const body = content.filter(Boolean).map((line) => line.startsWith('- ') ? line : `- ${line}`).join('\n') || '- Não informado.';
  return `## ${title}\n\n${body}\n`;
}

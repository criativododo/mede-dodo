import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { atomicWrite, nowIso, readJson } from './core.mjs';
import { projectPaths } from './documents.mjs';

const SIX_HOURS_MS = 6 * 60 * 60 * 1000;
const BLOCK_PATTERN = /```google_drive_sync\n([\s\S]*?)```/;

/**
 * Critério de relevância documental (item 2 do pedido de governança do /drive):
 * qualquer `.md` de documentação de arquitetura/produto — README, PROGRESS, TIMELINE,
 * DUMMY, FINDER-*, guias, specs avulsas etc., o que cada projeto de fato tiver — mais
 * as subpastas técnicas dedicadas (`specs/`, `decisions/`, `issues/`). Cada projeto
 * deste ecossistema guarda essa documentação de um jeito: alguns na raiz
 * (`mede-dodo`: `specs/`, `decisions/` na raiz), outros achatados sob `docs/`
 * (`dita-dodo`: `docs/DUMMY.md`, `docs/specs/`, `docs/decisions/`). Por isso o motor
 * procura em ambos os lugares — raiz do projeto e um nível dentro de `docs/` — e
 * sempre espelha com o nome canônico (`specs/`, `decisions/`, `issues/`, e `.md`
 * soltos na raiz do espelho), nunca replicando o prefixo `docs/` no destino: é a
 * mesma pasta lógica, só a origem que difere. Nunca código, build ou segredos.
 * Diretórios como `.venv/`, `dist/`, `node_modules/`, `__pycache__/`, `data/`,
 * `legado/` e `docs/legado/` nem são percorridos — ficam de fora por não pertencerem
 * a nenhuma das listas abaixo. `CLAUDE.md` é o único `.md` de raiz explicitamente
 * excluído — é configuração do agente, não conhecimento de produto.
 */
const ROOT_MD_EXCLUDE = new Set(['CLAUDE.md']);
const DOC_SUBDIRS = ['specs', 'decisions', 'issues'];

function listMarkdownFilesRecursive(absoluteDir, relativeDir) {
  if (!existsSync(absoluteDir)) return [];
  const results = [];
  for (const entry of readdirSync(absoluteDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const entryRelative = relativeDir ? `${relativeDir}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      results.push(...listMarkdownFilesRecursive(join(absoluteDir, entry.name), entryRelative));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      results.push(entryRelative);
    }
  }
  return results;
}

/**
 * Enumera, a partir da raiz do projeto, os documentos elegíveis para o espelho do
 * Drive. Cada item é `{ source, dest }`: `source` é o caminho real (relativo à raiz
 * do projeto) de onde ler o conteúdo; `dest` é o caminho canônico (relativo à raiz do
 * espelho) para onde gravar — sempre sem o prefixo `docs/`. Em empate de `dest` (o
 * mesmo documento existindo tanto na raiz quanto sob `docs/`), a raiz do projeto tem
 * precedência.
 */
export function planDriveSync(root) {
  const entries = [];
  const seenDest = new Set();
  const addEntry = (source, dest) => {
    if (seenDest.has(dest)) return;
    seenDest.add(dest);
    entries.push({ source, dest });
  };

  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.isFile() && entry.name.endsWith('.md') && !ROOT_MD_EXCLUDE.has(entry.name)) {
      addEntry(entry.name, entry.name);
    }
  }

  const docsDir = join(root, 'docs');
  if (existsSync(docsDir)) {
    for (const entry of readdirSync(docsDir, { withFileTypes: true })) {
      if (entry.isFile() && entry.name.endsWith('.md')) addEntry(`docs/${entry.name}`, entry.name);
    }
  }

  for (const name of DOC_SUBDIRS) {
    for (const [candidateRoot, prefix] of [[join(root, name), ''], [join(root, 'docs', name), 'docs/']]) {
      for (const relPath of listMarkdownFilesRecursive(candidateRoot, name)) {
        addEntry(`${prefix}${relPath}`, relPath);
      }
    }
  }

  return entries.sort((a, b) => a.dest.localeCompare(b.dest));
}

/**
 * Cópia idempotente (item 3 do pedido): compara o sha-256 de cada `source` elegível
 * com o manifesto da sincronização anterior (indexado por `dest`) e só grava no Drive
 * o que é novo ou mudou. Nunca remove do Drive um arquivo que não tem mais
 * correspondente local — o espelho só cresce ou atualiza, para não apagar por engano
 * algo que outra pessoa tenha colocado lá.
 */
export function syncDriveFiles({ root, destFolder, entries, previousManifest = {} }) {
  const manifest = {};
  const synced = [];
  const skipped = [];
  for (const { source, dest } of entries) {
    const content = readFileSync(join(root, source));
    const hash = createHash('sha256').update(content).digest('hex');
    manifest[dest] = hash;
    const destPath = join(destFolder, dest);
    if (previousManifest[dest] === hash && existsSync(destPath)) {
      skipped.push(dest);
      continue;
    }
    mkdirSync(dirname(destPath), { recursive: true });
    writeFileSync(destPath, content);
    synced.push(dest);
  }
  return { manifest, synced, skipped };
}

/**
 * O CLAUDE.md local (ou equivalente de especificação do projeto) é a única fonte de
 * verdade sobre se este projeto sincroniza documentação com o Google Drive: sem o bloco
 * declarativo ```google_drive_sync, nenhuma tentativa de sincronização é considerada.
 * Formato mínimo dentro do bloco (uma chave por linha, `chave: valor`):
 *
 *   ```google_drive_sync
 *   path: /caminho/absoluto/para/a/pasta/no/Drive
 *   ```
 */
export function readDriveConfig(root) {
  const claudeMdPath = join(root, 'CLAUDE.md');
  if (!existsSync(claudeMdPath)) return null;
  const match = readFileSync(claudeMdPath, 'utf8').match(BLOCK_PATTERN);
  if (!match) return null;
  const config = {};
  for (const rawLine of match[1].split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const separator = line.indexOf(':');
    if (separator === -1) continue;
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    if (key) config[key] = value;
  }
  return config.path ? config : null;
}

export function readDriveSyncState(memoryPath, projectId) {
  return readJson(projectPaths(memoryPath, projectId).driveState, { lastSyncedAt: null, files: {} });
}

/**
 * `files` é o manifesto relPath→sha256 da última cópia bem-sucedida. Quando omitido (ex.:
 * marcação manual via `/fim` ou `drive --mark`, sem passar por `planDriveSync`/`syncDriveFiles`),
 * preserva o manifesto anterior — só o timestamp muda.
 */
export function markDriveSynced(memoryPath, projectId, when = nowIso(), files) {
  const previous = readDriveSyncState(memoryPath, projectId);
  const state = { lastSyncedAt: when, files: files ?? previous.files ?? {} };
  atomicWrite(projectPaths(memoryPath, projectId).driveState, JSON.stringify(state, null, 2));
  return state;
}

/**
 * Regra de sincronização (item 3 do pedido): apenas por comando manual explícito ou quando
 * o intervalo desde a última sincronização já atingiu 6 horas. Sem o mapeamento declarativo,
 * a sincronização nunca é considerada — não há "acionamento automático implícito".
 */
export function evaluateDriveSync({ config, state, manualTrigger = false, now = new Date() }) {
  if (!config) return { active: false, due: false, reason: 'Projeto sem mapeamento google_drive_sync no CLAUDE.md local.' };
  const lastSyncedAt = state?.lastSyncedAt ? new Date(state.lastSyncedAt) : null;
  const elapsedMs = lastSyncedAt ? now.getTime() - lastSyncedAt.getTime() : Infinity;
  const due = manualTrigger || elapsedMs >= SIX_HOURS_MS;
  return {
    active: true,
    folder: config.path,
    notebookUrl: config.notebooklm_url ?? null,
    lastSyncedAt: state?.lastSyncedAt ?? null,
    due,
    reason: manualTrigger
      ? 'Comando manual ("sincronizar Drive").'
      : due
        ? 'Intervalo de 6h desde a última sincronização já decorrido.'
        : 'Nem comando manual nem intervalo de 6h decorrido — aguardar.',
  };
}

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { atomicWrite, nowIso, readJson } from './core.mjs';
import { projectPaths } from './documents.mjs';

const SIX_HOURS_MS = 6 * 60 * 60 * 1000;
const BLOCK_PATTERN = /```google_drive_sync\n([\s\S]*?)```/;

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
  return readJson(projectPaths(memoryPath, projectId).driveState, { lastSyncedAt: null });
}

export function markDriveSynced(memoryPath, projectId, when = nowIso()) {
  const state = { lastSyncedAt: when };
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
    lastSyncedAt: state?.lastSyncedAt ?? null,
    due,
    reason: manualTrigger
      ? 'Comando manual ("sincronizar Drive").'
      : due
        ? 'Intervalo de 6h desde a última sincronização já decorrido.'
        : 'Nem comando manual nem intervalo de 6h decorrido — aguardar.',
  };
}

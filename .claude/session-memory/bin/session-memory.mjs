#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve } from 'node:path';
import { fail, parseArgs, parseJson, print, readJson, nowIso, dateParts, estimateCost, SessionMemoryError } from '../lib/core.mjs';
import { loadConfig } from '../lib/config.mjs';
import { resolveProjectId } from '../lib/project.mjs';
import {
  ensureGitRepository, git, sourceSnapshot, changedFilesFromGitState, commitsSinceHead,
  resolveMemoryBranch, addSessionWorktree, removeSessionWorktree,
} from '../lib/git.mjs';
import {
  projectPaths, listJournals, nextJournalPath, regenerateExecutiveSummary, archiveExcessJournals,
  validateMemory, withMarker, readMarker, journalSection, deriveState,
} from '../lib/documents.mjs';
import { publishSessionWorktree } from '../lib/publish.mjs';
import { createInitialMemory } from '../lib/scaffold.mjs';
import { readDriveConfig, readDriveSyncState, markDriveSynced, evaluateDriveSync } from '../lib/drive.mjs';

const root = process.cwd();
const [command, ...rest] = process.argv.slice(2);
const args = parseArgs(rest);

function configFor(commandArgs) {
  const config = loadConfig(root);
  if (commandArgs['memory-dir']) config.memoryPath = resolve(root, commandArgs['memory-dir']);
  return config;
}

function projectIdFor(commandArgs) {
  return resolveProjectId(root, { override: commandArgs.project });
}

function memoryHasHistory(memoryPath) {
  return typeof git(['rev-parse', '--verify', 'HEAD'], memoryPath, { allowFailure: true }) === 'string';
}

function commitAndPushBootstrap(config) {
  git(['add', '-A'], config.memoryPath);
  git(['commit', '-m', 'docs(memory): initialize session memory'], config.memoryPath);
  if (typeof git(['push', '-u', 'origin', 'HEAD'], config.memoryPath, { allowFailure: true }) !== 'string') {
    fail('Memória inicializada localmente, mas o push falhou. Corrija o remoto e execute /fim novamente.');
  }
}

/**
 * Bootstrap do repositório de memória (hub compartilhado por qualquer projeto). Não conhece
 * nem escreve nada específico de um `projectId` — cada projeto ganha sua pasta sob
 * `projects/<projectId>/` de forma preguiçosa, na primeira publicação daquele projeto.
 */
function ensureMemoryRepository(config) {
  if (!existsSync(config.memoryPath)) {
    mkdirSync(resolve(config.memoryPath, '..'), { recursive: true });
    git(['clone', config.memoryRepositoryUrl, config.memoryPath], root);
  }
  ensureGitRepository(config.memoryPath, 'Repositório de memória');
  if (git(['status', '--porcelain=v1'], config.memoryPath)) {
    fail('O repositório de memória (hub) possui alterações não commitadas. Investigue antes de continuar.');
  }
  if (!memoryHasHistory(config.memoryPath) || !existsSync(join(config.memoryPath, 'README.md'))) {
    createInitialMemory(config.memoryPath);
    commitAndPushBootstrap(config);
    return { initialized: true };
  }
  return { initialized: false };
}

function fetchHub(config) {
  if (typeof git(['fetch', '--prune'], config.memoryPath, { allowFailure: true }) !== 'string') {
    fail('Não foi possível consultar o remoto da memória.');
  }
}

function refreshHubForReading(config) {
  fetchHub(config);
  const branch = resolveMemoryBranch(config.memoryPath, config.memoryBranch);
  git(['reset', '--hard', `origin/${branch}`], config.memoryPath, { allowFailure: true });
  return branch;
}

/** Lê apenas o executive-summary.md do projeto ativo — nunca o repositório de memória inteiro. */
function readExecutiveSummary(memoryPath, projectId) {
  const summaryPath = projectPaths(memoryPath, projectId).executiveSummary;
  if (!existsSync(summaryPath)) return deriveState([], projectId);
  return readMarker(readFileSync(summaryPath, 'utf8'), `projects/${projectId}/executive-summary.md`);
}

function listLines(values, empty = 'Nenhum.') { return values?.length ? values : [empty]; }

function makeJournal({ details, changes, commits, endedAt, source }) {
  const parts = dateParts(endedAt);
  const objective = details.objective || `Sessão encerrada em ${source.branch}`;
  const tests = details.checks?.length
    ? details.checks.map((item) => `${item.status === 'passed' ? 'Concluído' : item.status === 'not_configured' ? 'Parcial' : 'Bloqueado'} — \`${item.command}\` (${item.package}): ${item.evidence}`)
    : ['Não executado nesta sessão.'];
  const meta = {
    schemaVersion: 2, objective, endedAt, localEndedAt: `${parts.localDate} ${parts.hhmm.slice(0, 2)}:${parts.hhmm.slice(2)} BRT`,
    phase: details.phase, sprint: details.sprint, status: details.status || 'Parcial',
    confidence: details.confidence?.level || 'Não informada', blockers: details.blockers ?? [],
    nextTask: details.nextTask, adrsAffected: details.adrsAffected ?? [], summary: details.statusSummary || details.summary || null,
    source: { branch: source.branch, head: source.head, workingTree: source.status ? 'alterada' : 'limpa', commits: commits.map((commit) => commit.hash) },
    tags: details.tags || [], costEstimate: details.costEstimate ?? null,
  };
  const commitLines = commits.length ? commits.map((commit) => `\`${commit.shortHash}\` — ${commit.subject}`) : ['Nenhum commit criado nesta sessão.'];
  const body = [
    `# Journal — ${objective}`, '', withMarker('', meta).trimEnd(), '', journalSection('Objetivo', objective),
    journalSection('Contexto', details.context || 'Não informado.'), journalSection('Trabalhos realizados', listLines(details.workPerformed, 'Não informado.')),
    journalSection('Arquivos alterados', listLines(changes.modified)), journalSection('Arquivos criados', listLines(changes.created)),
    journalSection('Arquivos removidos', listLines(changes.removed)), journalSection('Commits', commitLines), journalSection('Testes', tests),
    journalSection('Decisões', listLines(details.decisions, 'Nenhuma decisão nova registrada.')), journalSection('ADRs afetadas', listLines(details.adrsAffected, 'Nenhuma ADR afetada.')),
    journalSection('Problemas encontrados', listLines(details.problems, 'Nenhum problema informado.')), journalSection('Bloqueios', listLines(details.blockers, 'Nenhum bloqueio informado.')),
    journalSection('Próxima tarefa', details.nextTask || 'Não informada.'), journalSection('Observações', listLines(details.observations, 'Nenhuma observação adicional.')),
    journalSection('Confiança da IA', `${details.confidence?.level || 'Não informada'}${details.confidence?.reason ? ` — ${details.confidence.reason}` : ''}`),
  ];
  return { meta, content: body.join('\n') };
}

function createEphemeralWorktree(config, memoryBranch) {
  const container = mkdtempSync(join(tmpdir(), 'criativododo-memory-'));
  const worktree = join(container, 'worktree');
  addSessionWorktree(config.memoryPath, worktree, `origin/${memoryBranch}`);
  return worktree;
}

function withEphemeralWorktree(config, run) {
  const memoryBranch = resolveMemoryBranch(config.memoryPath, config.memoryBranch);
  const worktree = createEphemeralWorktree(config, memoryBranch);
  try {
    return run(worktree, memoryBranch);
  } finally {
    removeSessionWorktree(config.memoryPath, worktree);
    rmSync(dirname(worktree), { recursive: true, force: true });
  }
}

function readFimDetails(commandArgs) {
  if (!commandArgs['details-stdin']) fail('Informe --details-stdin e envie os detalhes JSON pelo stdin.');
  return parseJson(readFileSync(0, 'utf8'), 'detalhes recebidos pelo stdin');
}

function commandInicio(commandArgs) {
  const config = configFor(commandArgs);
  ensureGitRepository(root, 'Repositório da aplicação');
  const result = ensureMemoryRepository(config);
  refreshHubForReading(config);
  const projectId = projectIdFor(commandArgs);
  const state = readExecutiveSummary(config.memoryPath, projectId);
  const validation = validateMemory(config.memoryPath, projectId);
  const journalWindow = config.journalWindow ?? 3;
  const journals = listJournals(config.memoryPath, projectId).slice(0, journalWindow);
  const driveConfig = readDriveConfig(root);
  const driveState = readDriveSyncState(config.memoryPath, projectId);
  const payload = {
    initializedMemory: result.initialized,
    project: projectId,
    executiveSummary: {
      phase: state.phase, sprint: state.sprint, blockers: state.blockers,
      lastArchitecturalDecision: state.lastAdr, lastRelevantCommit: state.lastCommit,
      recommendedNextTask: state.nextTask, latestJournals: journals.map((journal) => ({ path: journal.relativePath, objective: journal.meta.objective, endedAt: journal.meta.endedAt })),
    },
    driveSync: evaluateDriveSync({ config: driveConfig, state: driveState }),
    consistency: validation.valid ? 'ok' : validation.errors,
  };
  // Custo desta execução, para acompanhar regressão entre sessões (repasse este número ao /fim em details.costEstimate).
  print({ ...payload, costEstimate: estimateCost(payload) });
}

function commandStatus(commandArgs) {
  const config = configFor(commandArgs); ensureGitRepository(config.memoryPath, 'Repositório de memória'); refreshHubForReading(config);
  const projectId = projectIdFor(commandArgs);
  const state = readExecutiveSummary(config.memoryPath, projectId);
  const latest = listJournals(config.memoryPath, projectId)[0];
  print({ project: projectId, sprint: state.sprint, phase: state.phase, latestJournal: latest?.relativePath ?? 'Nenhum', lastCommit: state.lastCommit, lastAdr: state.lastAdr, blockers: state.blockers, nextTask: state.nextTask });
}

function commandJournal(commandArgs) {
  const config = configFor(commandArgs); ensureGitRepository(config.memoryPath, 'Repositório de memória'); refreshHubForReading(config);
  const projectId = projectIdFor(commandArgs);
  const journals = listJournals(config.memoryPath, projectId).filter((journal) => {
    const haystack = `${journal.relativePath}\n${journal.content}`.toLocaleLowerCase('pt-BR');
    return (!commandArgs.date || journal.relativePath.includes(commandArgs.date)) && (!commandArgs.sprint || journal.meta.sprint === commandArgs.sprint) && (!commandArgs.phase || journal.meta.phase === commandArgs.phase) && (!commandArgs.search || haystack.includes(String(commandArgs.search).toLocaleLowerCase('pt-BR')));
  });
  if (commandArgs.open) { const journal = journals.find((item) => item.relativePath === commandArgs.open || item.relativePath.endsWith(`/${commandArgs.open}`)); if (!journal) fail(`Journal não encontrado: ${commandArgs.open}`); print(journal.content); return; }
  print(journals.map((journal) => ({ path: journal.relativePath, objective: journal.meta.objective, phase: journal.meta.phase, sprint: journal.meta.sprint, endedAt: journal.meta.endedAt })));
}

/**
 * Sem conteúdo hardcoded: mostra `projects/<projectId>/roadmap.md` somente se o próprio
 * projeto já mantiver esse documento (marcador session-memory com `phases[]`). Sem esse
 * arquivo, informa a lacuna em vez de inventar fases genéricas.
 */
function commandRoadmap(commandArgs) {
  const config = configFor(commandArgs); ensureGitRepository(config.memoryPath, 'Repositório de memória'); refreshHubForReading(config);
  const projectId = projectIdFor(commandArgs);
  const roadmapPath = join(projectPaths(config.memoryPath, projectId).root, 'roadmap.md');
  if (!existsSync(roadmapPath)) {
    print({ project: projectId, configured: false, note: 'Nenhum projects/<id>/roadmap.md para este projeto. Não é gerado automaticamente; crie-o com o marcador session-memory (schemaVersion, phases[]) se quiser acompanhamento por fases.' });
    return;
  }
  const roadmap = readMarker(readFileSync(roadmapPath, 'utf8'), `projects/${projectId}/roadmap.md`);
  const phases = roadmap.phases ?? [];
  const completed = phases.filter((phase) => phase.status === 'complete');
  const active = phases.filter((phase) => phase.status === 'in_progress');
  print({
    project: projectId, configured: true,
    completion: phases.length ? `${completed.length}/${phases.length} (${Math.round((completed.length / phases.length) * 100)}%)` : '0/0',
    current: active, next: phases.filter((phase) => phase.status === 'pending').slice(0, 3), phases,
  });
}

function commandCheck(commandArgs) {
  const config = configFor(commandArgs); const requested = commandArgs.scope ? String(commandArgs.scope).split(',') : Object.keys(config.checks); const results = [];
  for (const packageName of requested) {
    const commands = config.checks[packageName]; if (!commands) { results.push({ package: packageName, command: '—', status: 'not_configured', evidence: 'Escopo não configurado.' }); continue; }
    const packageManifest = readJson(join(root, packageName, 'package.json'), {}); if (!packageManifest.scripts?.lint) results.push({ package: packageName, command: 'npm run lint', status: 'not_configured', evidence: 'O package.json não define script de lint.' });
    for (const checkCommand of commands) { const [binary, ...commandArgsList] = checkCommand.split(' '); const response = spawnSync(binary, commandArgsList, { cwd: join(root, packageName), encoding: 'utf8', shell: false }); const output = `${response.stdout ?? ''}${response.stderr ?? ''}`.trim().replace(/\s+/g, ' '); results.push({ package: packageName, command: checkCommand, status: response.status === 0 ? 'passed' : 'failed', evidence: output ? output.slice(-500) : response.status === 0 ? 'Concluído sem saída.' : `Código ${response.status ?? 'desconhecido'}.` }); }
  }
  print({ checks: results, note: 'Resultado efêmero: inclua-o nos detalhes enviados pelo stdin ao /fim se precisar registrá-lo no journal.' }); if (results.some((result) => result.status === 'failed')) process.exitCode = 1;
}

function commandFim(commandArgs) {
  const config = configFor(commandArgs); ensureGitRepository(root, 'Repositório da aplicação'); ensureMemoryRepository(config); fetchHub(config);
  const projectId = projectIdFor(commandArgs);
  const details = readFimDetails(commandArgs);
  for (const field of ['phase', 'sprint', 'nextTask']) if (!details[field]) fail(`Campo obrigatório ausente nos detalhes enviados pelo stdin: ${field}`);
  const endedAt = nowIso(); const source = sourceSnapshot(root); const changes = changedFilesFromGitState(root); const commits = commitsSinceHead(root); const journal = makeJournal({ details, changes, commits, endedAt, source });
  const archiveThreshold = config.archiveThreshold ?? 5;
  // Sufixo é um nonce de publicação, não um Session ID: só evita que duas transações
  // concorrentes escolham o mesmo nome antes de enxergarem o commit remoto.
  const publicationNonce = randomUUID().slice(0, 8);
  const result = withEphemeralWorktree(config, (worktree, memoryBranch) => {
    let journalRelativePath;
    let archived = [];
    const publish = publishSessionWorktree({
      worktree, remoteBranch: memoryBranch, message: commandArgs.message || 'docs(memory): registra sessão',
      prepareCommit: (wt) => {
        const journalPath = nextJournalPath(wt, projectId, endedAt, publicationNonce);
        journalRelativePath = relative(wt, journalPath).split('\\').join('/');
        mkdirSync(dirname(journalPath), { recursive: true });
        writeFileSync(journalPath, journal.content, 'utf8');
        regenerateExecutiveSummary(wt, projectId);
        archived = archiveExcessJournals(wt, projectId, archiveThreshold).archived;
        if (commandArgs['drive-synced'] || details.driveSyncPerformed) markDriveSynced(wt, projectId, endedAt);
        const validation = validateMemory(wt, projectId); if (!validation.valid) fail(`Publicação bloqueada: ${validation.errors.join('; ')}`);
      },
    });
    return { ...publish, journal: journalRelativePath, archived };
  });
  const fimPayload = { ...result, project: projectId, changes: { modified: changes.modified, created: changes.created, removed: changes.removed }, commits, note: 'Transação concluída: journal, resumo executivo, arquivamento (se aplicável), commit, push e limpeza do worktree.' };
  print({ ...fimPayload, costEstimate: { fim: estimateCost(fimPayload), inicio: details.costEstimate ?? null } });
}

function commandDrive(commandArgs) {
  const config = configFor(commandArgs); ensureGitRepository(root, 'Repositório da aplicação'); ensureMemoryRepository(config); refreshHubForReading(config);
  const projectId = projectIdFor(commandArgs);
  const driveConfig = readDriveConfig(root);

  if (commandArgs.mark) {
    if (!driveConfig) fail('Nenhum mapeamento google_drive_sync no CLAUDE.md deste projeto; nada a marcar.');
    let markedAt;
    const result = withEphemeralWorktree(config, (worktree, memoryBranch) => publishSessionWorktree({
      worktree, remoteBranch: memoryBranch, message: 'docs(memory): registra sincronização manual do Drive',
      prepareCommit: (wt) => { markedAt = nowIso(); markDriveSynced(wt, projectId, markedAt); },
    }));
    print({ project: projectId, ...result, driveSync: evaluateDriveSync({ config: driveConfig, state: { lastSyncedAt: markedAt }, manualTrigger: true }) });
    return;
  }

  const state = readDriveSyncState(config.memoryPath, projectId);
  print({ project: projectId, ...evaluateDriveSync({ config: driveConfig, state, manualTrigger: Boolean(commandArgs.sync) }) });
}

function commandValidate(commandArgs) {
  const config = configFor(commandArgs); ensureGitRepository(config.memoryPath, 'Repositório de memória'); refreshHubForReading(config);
  const projectId = projectIdFor(commandArgs);
  const result = validateMemory(config.memoryPath, projectId); print(result); if (!result.valid) process.exitCode = 1;
}

const handlers = { inicio: commandInicio, fim: commandFim, status: commandStatus, journal: commandJournal, roadmap: commandRoadmap, check: commandCheck, drive: commandDrive, validate: commandValidate };
try { if (!command || command === 'help') print('Uso: session-memory.mjs <inicio|fim|status|journal|roadmap|check|drive|validate>'); else if (!handlers[command]) fail(`Comando desconhecido: ${command}`); else handlers[command](args); } catch (error) { if (error instanceof SessionMemoryError) { process.stderr.write(`ERRO: ${error.message}\n`); process.exitCode = 1; } else throw error; }

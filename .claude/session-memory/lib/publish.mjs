import { fail } from './core.mjs';
import { git } from './git.mjs';

const DEFAULT_MAX_ATTEMPTS = 5;

/**
 * Publica o commit da sessão no repositório de memória com retry de
 * fetch → reset-para-o-remoto → regenerar → commit → push (ADR-021, Fase 3).
 *
 * Cada tentativa reconstrói o commit do zero em cima do estado mais recente do remoto —
 * não existe "rebase" de um commit antigo sobre outro: como cada sessão só grava seu
 * próprio journal (nome único por sessão) e os três artefatos derivados são sempre
 * regenerados (nunca mesclados por diff), reconstruir do zero a cada tentativa é mais
 * simples e mais robusto do que resolver conflitos — não há o que conflitar por
 * construção. Nunca faz force-push: se o remoto avançar mais rápido do que conseguimos
 * publicar depois de `maxAttempts` tentativas, falha alto e para (ADR-018).
 *
 * `prepareCommit(worktree)` é chamado a cada tentativa, sempre depois do reset para a
 * branch remota resolvida — deve recriar o journal da sessão e regenerar os artefatos derivados
 * contra o conjunto de journals então presente (que já inclui qualquer sessão concorrente
 * que tenha publicado primeiro).
 */
export function publishSessionWorktree({ worktree, remoteBranch, message, prepareCommit, maxAttempts = DEFAULT_MAX_ATTEMPTS, gitFn = git }) {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const fetch = gitFn(['fetch', 'origin', remoteBranch], worktree, { allowFailure: true });
    if (typeof fetch !== 'string') fail('Não foi possível consultar o remoto da memória. Nenhuma alteração local foi perdida.');
    gitFn(['reset', '--hard', `origin/${remoteBranch}`], worktree);
    prepareCommit(worktree);
    const status = gitFn(['status', '--porcelain=v1'], worktree, { allowFailure: true });
    if (!status) return { published: false, reason: 'Nenhuma alteração para publicar.', attempts: attempt };
    gitFn(['add', '-A'], worktree);
    gitFn(['commit', '-m', message], worktree);
    const push = gitFn(['push', 'origin', `HEAD:refs/heads/${remoteBranch}`], worktree, { allowFailure: true });
    if (typeof push === 'string') {
      return { published: true, attempts: attempt, commit: gitFn(['rev-parse', '--short', 'HEAD'], worktree) };
    }
    // push rejeitado (provavelmente non-fast-forward: outra sessão publicou entre o
    // nosso fetch e o nosso push) — tenta de novo desde o fetch, nunca force-push.
  }
  fail(`Publicação da memória falhou após ${maxAttempts} tentativas: o remoto avançou mais rápido do que conseguimos publicar. Nenhum force-push foi tentado; execute /fim novamente.`);
}

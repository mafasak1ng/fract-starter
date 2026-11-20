#!/usr/bin/env node
/**
 * FRACT layer guard: the decision logic behind code/git-hooks/pre-commit.
 *
 * Usage (the pre-commit hook calls it; it is not meant to be run by hand):
 *   node layer-guard.mjs <work-dir> <repo-root>
 *
 * <work-dir> holds what the hook collected from Git:
 *   staged             the staged paths, NUL-separated
 *   has-head           present when the repository has a commit
 *   head-policy.json   _atlas/layers.json as committed at HEAD, when it exists
 *   index-policy.json  _atlas/layers.json as staged, when it exists
 *
 * Rules:
 *   - provenance paths (writable "never") never change, unlock or not;
 *   - kernel paths (writable "kernel") change only when ATLAS_TRIGGER holds one
 *     of kernel.triggers AND ATLAS_PASSKEY verifies against the scrypt record in
 *     kernel.passkey (constant-time compare);
 *   - every other path is not checked here.
 *
 * _atlas/layers.json and code/git-hooks/** always count as kernel, whatever the
 * policy says, so neither the policy nor this guard can change without the
 * unlock. The policy is read from HEAD; only a repository whose last commit has
 * no policy uses the staged one. While the committed policy has no passkey, a
 * commit whose staged policy differs from it only by a new passkey record is
 * checked against that new record: that is how init_vault.py's first passkey
 * gets committed.
 *
 * Every kernel or provenance decision is appended as one JSON line to
 * _atlas/audit/<YYYY-MM>.jsonl: { time, path, layer, allowed, reason, via }.
 * The passkey itself is never written or printed.
 *
 * Node.js 18 or newer, built-in modules only.
 */

import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { scryptSync, timingSafeEqual } from 'node:crypto';

const MANIFEST_PATH = '_atlas/layers.json';
const ALWAYS_KERNEL = [MANIFEST_PATH, 'code/git-hooks/**'];
const SCRYPT_DEFAULTS = { N: 16384, r: 8, p: 1 };
const SCRYPT_MAXMEM = 64 * 1024 * 1024;

const normalizePath = (value) =>
  String(value ?? '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/^\.\//, '')
    .replace(/^\/+/, '');

/** Pattern shapes: `dir/**` (everything under dir), `dir/*` (direct children), an exact path, or a bare folder. */
function matchesPattern(pattern, path) {
  const rule = normalizePath(pattern);
  const target = normalizePath(path);
  if (rule.length === 0) return false;
  if (rule.endsWith('/**')) {
    const prefix = rule.slice(0, -3);
    return target === prefix || target.startsWith(`${prefix}/`);
  }
  if (rule.endsWith('/*')) {
    const prefix = rule.slice(0, -2);
    if (!target.startsWith(`${prefix}/`)) return false;
    return !target.slice(prefix.length + 1).includes('/');
  }
  if (rule === target) return true;
  return target.startsWith(`${rule.replace(/\/+$/, '')}/`);
}

function parseManifest(text) {
  try {
    const document = JSON.parse(text);
    return document && typeof document === 'object' && document.layers && typeof document.layers === 'object'
      ? document
      : null;
  } catch {
    return null;
  }
}

/** The layer a path belongs to. The most specific (longest) matching pattern wins. */
function layerFor(manifest, path) {
  const target = normalizePath(path);
  if (ALWAYS_KERNEL.some((rule) => matchesPattern(rule, target))) {
    return { layer: 'kernel', writable: 'kernel' };
  }
  let best;
  for (const [name, entry] of Object.entries(manifest.layers)) {
    const paths = Array.isArray(entry?.paths) ? entry.paths : [];
    for (const pattern of paths) {
      if (!matchesPattern(pattern, target)) continue;
      const weight = normalizePath(pattern).length;
      if (!best || weight > best.weight) best = { weight, layer: name, writable: entry.writable };
    }
  }
  if (best) return { layer: best.layer, writable: best.writable };
  const name = typeof manifest.default === 'string' ? manifest.default : 'docs';
  return { layer: name, writable: manifest.layers[name]?.writable ?? 'permission' };
}

/** True when the passkey matches the scrypt record that init_vault.py wrote. */
function verifyPasskey(passkey, record) {
  if (!record || typeof record.hash !== 'string' || typeof record.salt !== 'string') return false;
  if (typeof passkey !== 'string' || passkey.length === 0) return false;
  const expected = Buffer.from(record.hash, 'hex');
  if (expected.length === 0) return false;
  try {
    const actual = scryptSync(passkey.normalize('NFKC'), Buffer.from(record.salt, 'hex'), expected.length, {
      N: Number(record.N) || SCRYPT_DEFAULTS.N,
      r: Number(record.r) || SCRYPT_DEFAULTS.r,
      p: Number(record.p) || SCRYPT_DEFAULTS.p,
      maxmem: SCRYPT_MAXMEM,
    });
    return actual.length === expected.length && timingSafeEqual(actual, expected);
  } catch {
    return false;
  }
}

/** The policy with its passkey blanked, to tell "only the passkey changed" from any other edit. */
const withoutPasskey = (manifest) =>
  JSON.stringify({ ...manifest, kernel: { ...(manifest.kernel ?? {}), passkey: null } });

const readOptional = (dir, name) => {
  const file = join(dir, name);
  return existsSync(file) ? readFileSync(file, 'utf8') : null;
};

function main(workDir, root) {
  const staged = readFileSync(join(workDir, 'staged'), 'utf8').split('\0').filter(Boolean);
  if (staged.length === 0) return 0;

  const hasHead = existsSync(join(workDir, 'has-head'));
  const headText = readOptional(workDir, 'head-policy.json');
  const indexText = readOptional(workDir, 'index-policy.json');
  const head = headText === null ? null : parseManifest(headText);
  const index = indexText === null ? null : parseManifest(indexText);

  if (headText !== null && !head) {
    console.error(`layer-guard: the committed ${MANIFEST_PATH} cannot be read, so no commit is accepted until it is repaired.`);
    return 1;
  }
  if (hasHead && !head && !index) {
    console.error(`layer-guard: no ${MANIFEST_PATH} in this branch, so the policy cannot be checked. Commit refused.`);
    return 1;
  }
  const manifest = head ?? index;
  if (!manifest) {
    console.error(`layer-guard: no ${MANIFEST_PATH} staged for the first commit; nothing to enforce yet.`);
    return 0;
  }

  const triggers = Array.isArray(manifest.kernel?.triggers)
    ? manifest.kernel.triggers.map((word) => String(word).trim()).filter(Boolean)
    : [];
  let record = manifest.kernel?.passkey && typeof manifest.kernel.passkey === 'object' ? manifest.kernel.passkey : null;
  let firstPasskey = false;
  if (!record && head && index?.kernel?.passkey && withoutPasskey(head) === withoutPasskey(index)) {
    record = index.kernel.passkey;
    firstPasskey = true;
  }

  const offered = String(process.env.ATLAS_TRIGGER ?? '').trim().toLowerCase();
  const triggerAccepted = offered.length > 0 && triggers.some((word) => offered.split(/\s+/).includes(word.toLowerCase()));
  let passkeyVerified = null;

  const decisions = [];
  for (const path of staged) {
    const target = layerFor(manifest, path);
    if (target.writable === 'never') {
      decisions.push({ path, layer: target.layer, allowed: false, reason: 'Provenance path: nothing changes it, not even an unlocked kernel.' });
      continue;
    }
    if (target.writable !== 'kernel') continue;
    let allowed = false;
    let reason;
    if (!record) {
      reason = 'The kernel has no passkey yet. Run python -B code/setup/init_vault.py, then commit _atlas/layers.json with code/setup/kernel_commit.py.';
    } else if (!triggerAccepted) {
      reason = triggers.length === 0
        ? 'The kernel has no trigger word configured, so nothing can unlock it.'
        : `The kernel needs a trigger word (${triggers.join(', ')}) in ATLAS_TRIGGER before a passkey is considered.`;
    } else {
      if (passkeyVerified === null) passkeyVerified = verifyPasskey(process.env.ATLAS_PASSKEY, record);
      allowed = passkeyVerified;
      reason = allowed
        ? `Trigger accepted and passkey verified${firstPasskey ? ' (first passkey)' : ''}.`
        : 'The trigger was accepted; the passkey did not match.';
    }
    decisions.push({ path, layer: target.layer, allowed, reason });
  }

  if (decisions.length === 0) return 0;

  const time = new Date().toISOString();
  try {
    const dir = join(root, '_atlas', 'audit');
    mkdirSync(dir, { recursive: true });
    const lines = decisions.map((d) =>
      JSON.stringify({ time, path: d.path, layer: d.layer, allowed: d.allowed, reason: d.reason, via: 'git-pre-commit' }),
    );
    appendFileSync(join(dir, `${time.slice(0, 7)}.jsonl`), `${lines.join('\n')}\n`, 'utf8');
  } catch (error) {
    console.error(`layer-guard: could not write the audit log (${error.message}).`);
  }

  const refused = decisions.filter((d) => !d.allowed);
  if (refused.length > 0) {
    console.error(`layer-guard: commit refused. ${refused.length} protected path(s) cannot change:`);
    for (const d of refused) console.error(`  [${d.layer}] ${d.path}\n      ${d.reason}`);
    console.error('\nTo commit kernel changes, stage them and run:');
    console.error('  python -B code/setup/kernel_commit.py -m "kernel: <what changed>"');
    console.error('Provenance paths cannot be unlocked.');
    return 1;
  }
  console.error(`layer-guard: ${decisions.length} kernel change(s) authorized${firstPasskey ? ' (first passkey set)' : ''}.`);
  return 0;
}

const [workDir, root] = process.argv.slice(2);
if (!workDir || !root) {
  console.error('layer-guard: run by code/git-hooks/pre-commit, which passes <work-dir> <repo-root>. Commit refused.');
  process.exit(1);
}
try {
  process.exit(main(workDir, root));
} catch (error) {
  console.error(`layer-guard: unexpected error, commit refused (${error.message}).`);
  process.exit(1);
}

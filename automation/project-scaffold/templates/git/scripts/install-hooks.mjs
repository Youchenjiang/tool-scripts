#!/usr/bin/env node
/**
 * scripts/install-hooks.mjs
 *
 * Installs version-controlled git hooks from scripts/hooks/ into .git/hooks/.
 * Runs automatically via `npm run prepare` on `npm install`.
 */

import { chmodSync, copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const gitDir = join(root, ".git");

// If not a git repo or running in shallow CI environment, skip gracefully
if (!existsSync(gitDir)) {
  process.exit(0);
}

const hooksDir = join(gitDir, "hooks");
const sourceHooksDir = join(root, "scripts", "hooks");

if (existsSync(sourceHooksDir)) {
  mkdirSync(hooksDir, { recursive: true });
  const hookNames = ["commit-msg", "pre-commit"];

  for (const name of hookNames) {
    const source = join(sourceHooksDir, name);
    const target = join(hooksDir, name);
    if (existsSync(source)) {
      copyFileSync(source, target);
      try {
        chmodSync(target, 0o755);
      } catch {
        // Windows filesystem chmod no-op
      }
      console.log(`[prepare] Installed git hook: .git/hooks/${name}`);
    }
  }
}

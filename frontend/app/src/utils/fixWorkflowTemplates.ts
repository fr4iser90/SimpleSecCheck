import type { ScanTargetItem } from '../hooks/useTargets'
import { formatTopSeverityLabel } from './fixTargetPrompt'

export function suggestedHeadBranch(target: ScanTargetItem): string {
  const d = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const short = target.id.replace(/-/g, '').slice(0, 8)
  return `fix/ssc-${d}-${short}`
}

export function defaultBaseBranch(target: ScanTargetItem): string {
  const b = target.config?.branch
  if (b != null && typeof b === 'string' && b.trim()) return b.trim()
  return 'main'
}

export function buildPRTitle(target: ScanTargetItem): string {
  const sev = formatTopSeverityLabel(target)
  return `security: address SimpleSecCheck findings (${sev})`
}

export function buildIssueTitle(target: ScanTargetItem): string {
  return `[Security] SimpleSecCheck findings — ${target.display_name || target.source}`
}

export function buildPRBodyMarkdown(
  draftPrompt: string,
  target: ScanTargetItem,
  scanId: string
): string {
  const label = target.display_name || target.source
  const safePrompt = draftPrompt.length > 80000 ? `${draftPrompt.slice(0, 80000)}\n\n…(truncated)` : draftPrompt
  return [
    '## Summary',
    '',
    'Remediation context generated from **SimpleSecCheck**.',
    '',
    `- **Scan ID:** \`${scanId}\``,
    `- **Target:** ${label}`,
    `- **Source:** ${target.source}`,
    '',
    '## Generated fix prompt',
    '',
    '```',
    safePrompt,
    '```',
    '',
    '## Checklist',
    '',
    '- [ ] Changes reviewed',
    '- [ ] CI / tests passing',
    '- [ ] Rescan or verification scan planned',
    '',
  ].join('\n')
}

export function buildIssueBodyMarkdown(draftPrompt: string, target: ScanTargetItem, scanId: string): string {
  const label = target.display_name || target.source
  const excerpt =
    draftPrompt.length > 12000 ? `${draftPrompt.slice(0, 12000)}\n\n…(full text in attached fix.md or PR)` : draftPrompt
  return [
    '## SimpleSecCheck',
    '',
    `**Scan ID:** \`${scanId}\``,
    `**Target:** ${label}`,
    '',
    '### Prompt / context',
    '',
    '```',
    excerpt,
    '```',
    '',
    '---',
    '*Create a branch and PR when ready; keep human review in the loop.*',
  ].join('\n')
}

export function buildPatchInstructionsMarkdown(
  headBranch: string,
  baseBranch: string,
  target: ScanTargetItem
): string {
  return [
    '# Patch workflow (local)',
    '',
    '```bash',
    `git fetch origin`,
    `git checkout -b ${headBranch} origin/${baseBranch}`,
    `# apply fixes, then:`,
    `git add -A && git commit -m "security: address findings (SimpleSecCheck)"`,
    `git push -u origin ${headBranch}`,
    '```',
    '',
    `Then open a pull request: **${baseBranch}** ← **${headBranch}**`,
    '',
    `- Target: ${target.display_name || target.source}`,
    `- Remote: ${target.source}`,
    '',
  ].join('\n')
}

export function buildHybridReadmeMarkdown(): string {
  return [
    '## Hybrid workflow (recommended)',
    '',
    '1. Use the generated **fix prompt** in your IDE or AI assistant.',
    '2. Create a **branch** and open a **pull request** — never merge silent auto-fixes without review.',
    '3. Let **GitHub Actions / GitLab CI** run tests and lint; that pipeline is the source of truth.',
    '4. Optionally trigger a **new SimpleSecCheck scan** on the PR branch after CI is green.',
    '',
    'Fully automated “agent fixes everything” flows require explicit trust boundaries and are out of scope for the default product path.',
  ].join('\n')
}

export function buildExampleGithubActionsYaml(): string {
  return [
    '# Example only — adapt to your instance and secrets.',
    '# Goal: remind humans to rescan after a security-related PR.',
    'name: Post-PR security reminder',
    'on:',
    '  pull_request:',
    '    types: [opened, synchronize]',
    '',
    'jobs:',
    '  remind:',
    '    runs-on: ubuntu-latest',
    '    steps:',
    '      - name: Rescan hint',
    '        run: |',
    '          echo "Trigger a SimpleSecCheck scan for this branch from your dashboard or API when ready."',
  ].join('\n')
}

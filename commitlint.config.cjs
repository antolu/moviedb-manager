module.exports = {
  extends: ['@commitlint/config-conventional'],
  // Skips linting for any commit starting with "chore(deps):"
  ignores: [(message) => message.includes('chore(deps):')],
}

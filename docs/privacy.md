# Repository privacy

Use anonymous commit author and committer metadata. This checkout uses
`Repository Maintainer <maintainer@example.invalid>`; no personal contact address
is needed for a local commit. Keep credentials in ignored environment files or
your deployment secret store, and keep server-specific details out of tracked
documentation. Use reserved example domains in samples.

The pre-commit hook and CI privacy guard inspect staged text for non-example
email addresses, recognizable credential formats, hardcoded secret assignments,
database credentials, and prohibited private paths. The hook also checks commit
identities. Rejections report counts, never matched values. Run:

```bash
git config --local core.hooksPath .githooks
node --test scripts/check-private-files.test.mjs
node scripts/check-private-files.mjs
```

For exact private names, domains or account identifiers, maintain an optional
local `.privacy-patterns.json` containing a JSON array of strings. The file is
ignored and the guard refuses to commit it. CI checks generic rules without
requiring access to private values. Pattern checks do not replace review.

History sanitization changes commit hashes. Any existing remote, fork, clone or
backup can still hold the old data until its owner replaces or removes that copy.
Do not merge an old unsanitized branch into rewritten history. Re-clone after a
coordinated remote history replacement. Revoke and rotate any real credentials
that were previously published; rewriting Git does not revoke credentials.

Historical local commit authors, committers, messages and tracked text were
sanitized, and historical private environment/upload paths were removed. The
local history verification checks every remaining ref and reachable object.
Remote history is not replaced automatically by the local operation.

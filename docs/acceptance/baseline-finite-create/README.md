# Public `baseline create` command lifetime

Evidence for the F-owner step that routes `bookscan baseline create PDF --workdir
PROJECT` through the existing internal `initial_import.create`, with its own
signal handlers, error mapping, frozen single result and delivery handling.

Product: `src/bookscan/finite_create.py` (new), `src/bookscan/finite_command.py`
(new, the shared `Control`/`Interrupted`/`signals`/`envelope` moved out of
`finite_status.py`), the create route in `src/bookscan/finite_protocol.py`, help
and unavailable text. Durable checks: `tests/test_finite_create.py` (16 cases),
`tests/finite_create_acceptance.py`; recipes `process:create`,
`process:create-check`, `process:create-acceptance`.

## What is observed

* `create-result.json.gz` — the installed-entry acceptance on actual native import
  of the seven constructed pages. The ordinary create commits and status after
  source loss reports the construction's RGB digests; an occupied destination is
  `PROJECT_EXISTS`/4 uncommitted; twelve installed writer PID barriers
  (asset-complete, checkpoint pre-commit, checkpoint post-commit with the
  progress latch set, native child alive) each under SIGINT/SIGTERM/SIGKILL.
  Caught signals return 130/143 with the exact committed fact; pre-commit caught
  signals leave no project; post-commit ones leave a verifying project; SIGKILL
  pre-commit leaves an incomplete directory that status reports `INVALID_PROJECT`/3
  and create refuses with 4; a SIGKILLed writer's separate-session child stays
  alive while ownership is immediately reacquirable and caught signals reap it.
  A real closed stdout returns 5 with one `RESULT_DELIVERY_FAILED`, and the
  project still commits and verifies.
* `mutants.json` — seven guard mutations of `finite_create.py`, each observed
  failing at least one `tests/test_finite_create.py` case; digest restored.
* `subjects.sha256`, `exits.txt` — digests of the product/test subjects before the
  sequential final readings and their verification after; every reading exited 0.

## Limits (not claims)

* The child-alive barrier delays the real `pdftocairo` exec behind `/bin/sh -c
  'sleep 30; exec "$@"'` so a child exists when the signal lands. It supplements,
  it does not replace, an installed renderer child that is mid-render.
* The private cache selection is a sitecustomize replacement of
  `native_setup.default_cache`; no public test mode or cache option exists.
* Source fidelity, packets, review actions, export and the browser are untouched.
  `complete_finite_handoff` stays false.

# AGENTS.md: rules for every agent working in this repository

Built by firstmate crewmates from `PLAN.md` (frozen method) and `plan/TASKS.md` (briefs). Your brief is your task's section in `plan/TASKS.md`.

1. **Prefer your lane.** Edit mainly the files your brief lists under "Owns". If you must touch shared code, keep it small and explain it in `reports/lanes/<ID>.md`. Rebase and resolve ordinary conflicts yourself.
2. **Don't edit `PLAN.md` §1–§11.** If the method seems wrong, write `reports/STOP.md` and stop.
3. **Real model calls only in Q0's probe, Q9 and Q14.** Tests use fakes or recordings; `make test` blocks the network.
4. **Secrets:** the key lives only in the file named by `FQA_ENV_FILE`. Never print environment variables, never read that file with shell tools, never put a key in a command line, log, trace, recording or commit. Run `make scan-secrets` before committing.
5. **Names:** `make scan-forbidden` must pass. Never name an employer or a private person.
6. **Numbers** on the dashboard and in the README come only from committed files in `results/`.
7. **Quality:** Python 3.12, `uv`, Ruff, mypy on `src/`, pytest; TypeScript strict and Vite for the dashboard. Small readable modules.
8. **Finish** with `reports/lanes/<ID>.md` (what, how tested, deviations, open issues) and a clean, ready branch.
9. **Never push, never add a remote, never publish.**

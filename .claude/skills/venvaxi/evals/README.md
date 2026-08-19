# venvaxi skill evals

Nine cases in `evals.json`, each seeded from a behaviour the skill documents - the workflow, a
gotcha, or the declared scope boundary. Case 9 is deliberately negative: the correct behaviour is
to answer from general knowledge and not manufacture AXI lookups.

## Running the suite

The suite is run through the `skill-creator` skill's eval tooling, not a bespoke runner:

1. Invoke skill-creator's eval runner over this directory - it launches an executor subagent per
   prompt with the skill loaded, grades each transcript against the case's `expectations` via
   `agents/grader.md`, and aggregates with `scripts/aggregate_benchmark.py`.
2. Read the failing expectations. Each one names the exact claim or behaviour that was missed.

## The improvement loop is manual, by design

1. Run the suite and collect the failures.
2. Edit **the packaged source** `src/venvaxi/SKILL.md` - never
   `.claude/skills/venvaxi/SKILL.md`, which is generated output.
3. Run `just skill-sync` to regenerate the repo copy through the real installer.
4. Land the change as a reviewed commit; `tests/test_skill_parity.py` keeps the copies honest.

No automated rewrite loop exists, deliberately. This project's review gates are the point - an
unattended loop rewriting a tracked file removes the human checkpoint the ICM workflow requires.
A pass-rate threshold would also be meaningless at this scale: with nine cases a single failure
is 11 points, so read the individual failures instead of chasing a percentage.

## Adding a case

Keep the existing schema exactly (`id`, `name`, `prompt`, `expected_output`, `files`,
`expectations`). Verify every factual claim in a new case against the installed venv first - an
eval whose expected answer is wrong is worse than no eval.

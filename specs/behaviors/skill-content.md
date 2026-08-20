---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [behavior, skill, ambient, agent-experience]
---

# Behavior: Packaged skill content

## Rule

The packaged skill is **derived** material. Every claim it makes about `venvaxi` restates
something `specs/**` already declares, so where the skill and a spec disagree, the skill is what
is wrong and the skill is what changes.

It is also the whole of the ambient context. Since the always-on `AGENTS.md` block was removed,
nothing else `venvaxi setup` installs describes the tool, and the skill's `description` is the
only thing deciding whether the AXI is reached for at all.

Those two facts set the bar. The skill is loaded into an agent's context on description match,
which spends the working budget of a task that has not started yet - so an entry earns its place
only if an agent, mid-task, would do something different for having read it.

## Applies to

`src/venvaxi/SKILL.md`, the packaged source. The installed copy `venvaxi setup` writes is
byte-identical to it by [`setup.md`](../commands/setup.md) Actions item 4, and this repository's
own copy at `.claude/skills/venvaxi/SKILL.md` is regenerated from it, so this spec governs all
three through the one source.

## Details

### What the skill may assert

- The packaged skill shall restate no claim about `venvaxi` behaviour that `specs/**` does not
  declare.
- The packaged skill shall describe the exit-code contract as the three outcomes
  [Output contract](output-contract.md#exit-codes) declares, so that exit `2` is distinguishable
  from a reported `Error` at exit `1`. An agent branching on `exit == 1` to mean 'handled error'
  otherwise misclassifies a venvaxi fault as a query it should retype.
- If a measurement, benchmark or comparison would not change what an agent runs next, then the
  packaged skill shall name where the figure lives rather than reproduce it. Such figures answer
  an evaluator's question - is this tool worth adopting - and the skill's reader has already
  adopted it.

### What the skill must cover

- The packaged skill shall state, for each alternative an agent reaches for instead of the AXI,
  why the AXI is preferred. Recalling the API from memory and executing the dependency to observe
  it are both in that set; naming only the first leaves the more common habit unaddressed.
- The packaged skill shall carry an entry for each observed failure mode that costs an agent a
  wasted query or a wrong conclusion, naming the correct move rather than only the symptom.
- Where the AXI cannot answer a class of question at all, the packaged skill shall say so
  plainly. A boundary is cheaper stated once than discovered by exhausting the surface.
- If a worked example demonstrates a query whose result an agent would misread, then the packaged
  skill shall demonstrate the unambiguous query instead.

### The description is the trigger surface

- The skill `description` shall name the situations calling for the AXI in terms of what the
  caller is doing, not in terms of what the AXI returns. An agent matches on the shape of its
  problem; a taxonomy of answers matches only a caller who already knows the tool.
- The skill `description` shall name debugging framings alongside authoring and review ones -
  observed misbehaviour whose cause is a signature fact the caller has not yet identified as one.
  That is the larger share of real work, and the share where version drift does the most damage.

## Out of scope

- **Automated detection of skill/code drift** - nothing compares the skill's claims against the
  CLI or `venvaxi --help`, so this spec is enforced at review.
  [#39](https://github.com/andyrids/venv-axi/issues/39) owns it, and until it lands every rule
  above is a rule a human checks.
- **Executing the eval suite** - `.claude/skills/venvaxi/evals/` is exercised by a human running
  the loop in its README, never by CI, so an eval case is a specimen rather than a gate.
  [#40](https://github.com/andyrids/venv-axi/issues/40) owns it.
- **A per-repo variation point** - declared Never in [`setup.md`](../commands/setup.md) Out of
  scope; byte-identity is what lets a parity check catch drift between the two copies.
- **Usage guidance** - tutorials, worked recipes and migration guides stay out of the skill for
  the same reason they stay out of the output, per
  [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it).

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 1, token-efficient output](../principles.md#principle-1-token-efficient-output)
  - the economy the AXI applies to its payloads applies to the skill describing them. A skill
  that is expensive to load taxes every task matching its description, including the ones it
  then fails to help.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - the measured figures live there, which is why the skill points at them rather than carrying
  them.

**Local**:

- **An entry earns its place only if an agent would act differently for having read it.** The
  test applies in both directions and is run at every edit: prose that is accurate, well argued
  and inert is cut, and a failure mode observed in the field is added even where its section is
  already the longest in the file. Length is not the measure - an agent that reads 10 lines and
  changes course got better value than one that reads two and does not.

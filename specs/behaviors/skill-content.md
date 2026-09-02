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

### What is machine-checked

The rules above are content rules, and most of them can only be judged by a reader. Some of what
the skill asserts has a counterpart in the code that can be diffed against it, and where one
exists the check exists too - four confirmed instances of the skill going stale
([#39](https://github.com/andyrids/venv-axi/issues/39)) were each caught by a person noticing,
which is not a mechanism.

- Where the packaged skill's command table names a flag, that flag shall be accepted by the
  command it is listed against, and any default the table states shall be that command's own
  default.
- Where the packaged skill's command table describes a command, it shall name every non-global
  flag that command accepts. Naming a flag that does not exist and omitting one that does are
  different failures, and only the second survives a reader checking the table against the tool.
- Where the packaged skill's MCP tool table names a tool, that tool shall exist under that name,
  and the parameters and defaults the table states shall be the ones it is registered with.
- Where the packaged skill states the exit-code contract, the codes it names there shall be
  exactly those [Output contract](output-contract.md#exit-codes) declares - neither fewer nor
  more. That paragraph was wrong three times inside one run; what recurred was *how many outcomes
  there are*, which is countable. An exit code named elsewhere in the skill is residue, below.
- Where the packaged skill documents a query together with the result it returns, that query shall
  be run against the venv the project installs for itself, and the property the example teaches
  shall hold of the result. No such query shall be absent from the set the gate runs or records as
  unexecutable - a set that is added to by hand goes stale in the one direction none of the
  parsed surfaces can.

Three limits belong to the rule rather than being exceptions to it:

- **A documented result is venv-dependent.** A recorded `count:` is what one version of a
  dependency returns and the next returns something else, so an executed check asserts what the
  example teaches - that the symbol the caller asked for leads the results - never equality
  against the recorded block. An assertion pinned to a frozen string reports a dependency upgrade
  as skill drift.
- **Where the packaged skill states a non-zero result count in prose, it shall name the results
  the example teaches by instead.** In prose a figure carries nothing the exemplars do not, and a
  figure no check can hold is a claim that goes stale unobserved. A fenced block reproducing real
  output is a different thing and keeps what it recorded - it is a specimen of the output shape,
  and the executed check above is what keeps it honest. `count: 0` is exempt: the definitive empty
  state is a fact [Output contract](output-contract.md#definitive-empty-states) declares, not a
  measurement of an installed version.
- **If a documented query names a package the project does not install, then it shall be recorded
  as unexecutable rather than passed over.** A check that silently covers four examples of five
  reports the same green as one that covers all five.

## Out of scope

- **Drift detection for a claim outside the four checked surfaces** - those surfaces are the
  command table, the MCP tool table, the exit-code contract statement, and the documented queries.
  A claim in prose outside all four stays enforced at review **even when it names a flag, an exit
  code or a tool**. `getSymbolTool`'s error wording going false under
  [#62](https://github.com/andyrids/venv-axi/issues/62) is the shape of it: prose in the MCP
  section, naming two tools, sitting in no table. So is a count of the read tools, an error string
  quoted from the code, and an exit code named in a gotcha rather than in the contract statement.

  **The residue is stated by surface, not by vocabulary, and that is the correction.** An earlier
  wording made it a question of which words a claim used - a claim "naming no flag, no exit code,
  no MCP tool and no runnable query" - which excluded from the residue the very `getSymbolTool`
  prose it cited to define the residue, and so reinstated the assumption this bullet exists to
  prevent: that a stale prose line was machine-checked. A rule assumed covered by a gate that
  structurally cannot see it is worse off than one known to be unchecked.
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

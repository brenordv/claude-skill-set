# Implicit state machines

An implicit state machine is behavior that depends on the current values of fields, flags, or
rows, with no one place in the code that lists the states and the legal moves between them.
statecharts.dev calls it an implied state machine: "there's no place in the code that you can point
to and say 'these are the different states'". The bugs it hides look alike. The program lands in a
combination of values nobody designed, through a path nobody drew, and the failure surfaces far
from the write that caused it.

This file is the catalog the `state-machine-auditor` skill applies, and any review or design that
touches state can use it directly: the signals say where to look, the flaw catalog says what
breaks, and the fix ladder says how small the fix can be. Writing the machine down pays for itself.
In an experiment with 30 participants on industrial embedded C functions, developers given
extracted state machine models answered more questions correctly and in less time (Said, Quante,
Koschke, ICPC 2019).

## Detection signals

A signal marks a candidate, not a finding. Run the "Not a finding" guards before mapping one.

- **S1 A status-like field written from more than one place.** A `status`, `state`, `phase`,
  `stage`, `step`, or `mode` field (enum, string, or int) that several functions, handlers, or
  services assign. Security vocabulary counts the same way: `verified`, `approved`, `active`,
  `locked`, `revoked`, `consumed`, `expired`, MFA and session state.
- **S2 Repeated switches.** The same switch or if-chain on that field in several places. Fowler
  and Beck's smell: "whenever you add a clause, ... you have to find all the switches and update
  them."
- **S3 Flags that exclude or combine.** Several booleans on one owner where only one should be
  true at a time, or whose combinations mean something. Nystrom: "When you have a handful of flags
  where only one is true at a time, that's a hint that what you really want is an enum."
- **S4 Nullable as state.** Optional fields or timestamps that are valid only in some states:
  `completedAt == null` means pending, or a state enum sits beside fields set only for some of its
  values. Wlaschin's clue is "an excessive number of nullable or option types"; the direction of
  the fix is Minsky's "make illegal states unrepresentable."
- **S5 Temporal coupling.** Members that only work in order: `Initialize` before use, nothing
  after `Dispose` or `Close`, `Start` once. Seemann defines it as an implicit relationship
  "requiring clients to invoke one member before the other." Typestate (Strom and Yemini) is the
  formal name for operations that are legal only in some states.
- **S6 Event-first handling.** A switch on the incoming event or action with defensive checks of
  the current state inside each case (Khourshid), or a reducer written "unconditionally", computing
  the next state from the action alone (Redux style guide, "Treat Reducers as State Machines").
- **S7 The UI guards a transition the logic doesn't own.** `disabled={isLoading}` stands in for
  "this event is not accepted in this state." Khourshid: "Disabling a button is not logic."
- **S8 A persisted status advanced by more than one process.** Message handlers, jobs, webhooks,
  or other services each move a row's status. The machine spans processes and nobody holds all of
  it.
- **S9 Bookkeeping that records history.** Retry counters, attempt ids, leases, locks,
  processed-id sets, and flags that remember what already happened. CPython's asyncio `Process`
  tracks `_communication_started` and `_input_written`; Node's writable stream packs its state into
  one bit-flag word (`kEnding`, `kEnded`, `kFinished`, `kWriting`). Mature libraries carry these
  on purpose; in application code they are often a machine nobody mapped.
- **S10 A flag added to make a symptom stop.** `if (_alreadyHandled) return;` fixes the reported
  bug and doubles the state space its owner can be in. The flag's combinations with every existing
  state are the part nobody checked. It is the easiest local fix to write, for people and agents
  alike, so check it first in a diff.

## Not a finding

- A single independent boolean that combines with nothing (`isOpen` on a modal).
- A field set once at construction and never changed.
- Configuration read once at startup.
- An explicit machine: a transition table, a state-machine library, Erlang's `gen_statem`, a
  typestate API. It is not flagged as implicit, but it still gets the flaw catalog.
- A status field with exactly one writer that guards every transition. It is not flagged as
  implicit, but its readers still get F1 and F9.

## Building the map

Use SCXML's vocabulary so maps read the same across repos: states, events, transitions with guard
conditions, initial and final states, compound (nested) states, parallel regions, and entry and
exit actions (W3C SCXML). Harel's statecharts extend plain state diagrams with hierarchy,
concurrency, and communication.

- Write each transition as from, to, trigger, guard, where it happens (`file:line`), and side
  effects.
- For a flag cluster of up to four flags, write the truth table and mark each row designed,
  reachable but undesigned, or unreachable. Past four (a bit-flag word), list the designed
  combinations and check every writer against them.
- When two dimensions vary independently (connection state and auth state), map them as parallel
  regions, not as one product enum.
- Every state needs a way in and, unless it is final, a way out. A state with no incoming
  transition is dead; a non-final state with no outgoing one is a trap.

## Flaw catalog

Each entry names the tell, how to check it, and its default severity. This catalog is the single
owner of severity for state-machine findings; the skill and `review-heuristics.md` point here.

- **F1 Unhandled state.** A reader has no arm for some state, or a default arm silently treats it
  as another state. Check every reader the trace found against the full state list. Important.
- **F2 Illegal combination, representable and reachable.** Exclusive flags both true; error and
  data both set; stale data rendered beside an error or in place of one. Find the writer sequence
  that reaches the row. Important when reachable, Suggestion when only representable.
- **F3 One state kept in several places.** A status column plus `isActive` plus `completedAt`; a
  widget's persisted state beside the model's copy; a client cache of server state. Find a writer
  that updates one copy and not the others. Important.
- **F4 Unguarded operation or transition.** A writer sets any state without checking the current
  one, so a final state moves backwards or a state gets skipped; or an operation valid in some
  states runs in another (use after `Dispose`, send after close). Important.
- **F5 Lost update.** Read the state, check it, write the next one, with nothing stopping a second
  writer in between. For persisted state the fix is a conditional write
  (`UPDATE ... SET state = @next WHERE id = @id AND state = @expected`) plus a row-count check.
  Important.
- **F6 Stuck state.** An in-flight state (`Processing`, `Sending`, `Locked`) with no timeout,
  reaper, or exit when the process dies mid-transition, or an error state with no way out.
  Important. A persisted in-flight state with no entered-at timestamp, so its age can't be measured
  or alerted on, is a Suggestion when the state has an exit and part of the Important finding when
  it has none; never flag that on in-memory state. Erlang's `gen_statem` makes the explicit form
  first-class: a state time-out "is automatically canceled when the state machine does a state
  change."
- **F7 Replay and reordering.** At-least-once delivery applies a transition twice, or events
  arrive out of order and an older event overwrites a newer state. Check each transition a message
  drives for an idempotency key or a version or sequence guard. Important.
- **F8 Side effect outside the transition.** The email, charge, or publish happens and the state
  write fails, or the reverse, and the retry repeats it. Check whether the effect and the write
  share a transaction, an outbox, or an idempotent receiver. Important; Critical for money or
  messages.
- **F9 New state not propagated.** F1 at the moment a state is added: every repeated switch (S2),
  serializer, database check constraint, API contract, frontend union, and report, plus rows that
  older versions stored and, in a rolling or mixed-version deploy, old code reading the new value.
  Important.
- **F10 Default value reads as a real state.** An unassigned enum is `0`, and `0` is `Pending`,
  so a row that never got a status looks valid. csharp Hard Rule 9 prevents this in C#; check the
  same shape in other languages and in database column defaults. Important.
- **F11 Wrong terminal or progress signal.** A transient failure settled into a final state, so
  the work is never retried (the failure-reads-as-success shape `coding-general.md` Hard Rule 10
  bans); a progress latch flipped because a step returned "ok" rather than because the state
  advanced; a recovery path that skips an item whose bookkeeping is missing instead of repairing
  it. Important.
- **F12 Lifetime mismatch.** Per-operation state held by a longer-lived owner (a field on a DI
  singleton, a module-level cache), or connection-scoped state (session locks, temp tables) used
  under a connection pool. Important.
- **F13 Torn transition.** An exception, early return, or `await` between two writes that
  together make one transition, or a re-entrant callback that observes the state half changed.
  Important.
- **F14 Security state.** Critical by default, and routed to the `security` skill as well:
  - a default arm, zero value, or catch that leaves or sets `verified`, `approved`, or `active`,
    so the check fails open;
  - a status field that request input can bind to (mass assignment);
  - a multi-step flow (password reset, MFA, checkout, approval) where a step skips the
    server-side check of the step before it, or only the UI enforces the order;
  - a gap between an authorization or account-state check and the act it guards;
  - per-user auth state held on a singleton;
  - a one-time token whose consume is not a compare-and-set, a token with no expiry, a revoked
    state some reader ignores, a session not rotated at login;
  - webhook-driven transitions accepted without a signature check and event-id idempotency.
- **F15 Untested machine.** Tests walk the happy path and never drive each transition or attempt
  an illegal one. Important for transitions the change adds (error arms also fall under
  `testing.md` Hard Rule 1); Suggestion otherwise.

Any entry is Critical when a reachable undesigned state corrupts persisted data, loses or
duplicates money, messages, or work, or fails open in a security decision.

A persisted or cross-process machine with no structured record of its transitions (from, to,
trigger, and a correlation id, which for S8 travels in the message envelope) is a Suggestion at
most, and never a finding on in-memory UI state. When a domain rule already requires an audit
trail, that rule sets the severity. Log shape: `review-heuristics.md` §Observability.

## Making it explicit

Suggest the smallest fix that closes the finding (`coding-general.md` Hard Rule 6). Walk the ladder
from the top and stop at the first rung that does it.

1. The local fix the F entry names: the missing arm, the guard or compare-and-set, the
   idempotency key, the timeout or entered-at timestamp, the default that can no longer read as a
   state.
2. Exhaustive dispatch, so the next new state fails the build. No arm may handle "everything
   else"; the only default allowed is one that asserts it is unreachable.
   - TypeScript: a discriminated union with a `never` assignment in the default branch, relying on
     "`never` turning up to do exhaustive checking."
   - Rust: `match` with no `_` arm; "the arms' patterns must cover all possibilities."
   - Python: a `match` or if-chain whose last branch calls `typing.assert_never` (3.11+), checked
     by the project's type checker.
   - C#: a switch expression with CS8509 ("does not handle all possible values") raised to an
     error, CS8524 (unnamed enum values) suppressed, and no discard arm. A discard arm matches every
     value, so CS8509 never fires, even when that arm throws, and a new member would compile. The
     compiler raises no exhaustiveness warning on switch statements, so the state dispatch has to
     be a switch expression.
3. Representation changes, as Suggestions, and in review mode only on code the change touches:
   - collapse exclusive flags into one status value and derive the booleans from it (Nystrom,
     Dodds);
   - put each state's data inside that state, so illegal combinations can't be built (sum types;
     where the language has none, one owner type with a guarded method per transition);
   - one transition function that switches on the current state first and the event second
     (Khourshid's finite-state-first approach; the Redux style guide), which is also the one place
     to emit the transition record.
4. Only when the cases demand it: typestate for call-order APIs, so misuse fails to compile
   (Biffle); the State pattern when per-state behavior is large, though it "can be overkill if a
   state machine has only a few states or rarely changes" (Refactoring Guru); statecharts when a
   flat enum would explode; a state-machine library only when the repo already uses one
   (Khourshid argues you don't need one).

For an explicit machine in production code, read hashicorp/raft: `RaftState` (`Follower`,
`Candidate`, `Leader`, `Shutdown`) is one typed value with atomic `getState` and `setState`
accessors.

## Sources

- statecharts.dev on implied state machines: https://statecharts.dev/benefit-explicit.html
- W3C, State Chart XML (SCXML), Recommendation, 2015: https://www.w3.org/TR/scxml/
- Harel, "Statecharts: A visual formalism for complex systems", Science of Computer Programming,
  1987: https://doi.org/10.1016/0167-6423(87)90035-9
- Strom and Yemini, "Typestate: A Programming Language Concept for Enhancing Software
  Reliability", IEEE TSE, 1986: https://doi.org/10.1109/TSE.1986.6312929
- Said, Quante, Koschke, "Do Extracted State Machine Models Help to Understand Embedded
  Software?", ICPC 2019: https://doi.org/10.1109/ICPC.2019.00038
- Nystrom, Game Programming Patterns, "State": https://gameprogrammingpatterns.com/state.html
- Wlaschin, "Designing with types: Making state explicit":
  https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/
- Minsky, "Effective ML": https://blog.janestreet.com/effective-ml/
- Seemann, "Design Smell: Temporal Coupling":
  https://blog.ploeh.dk/2011/05/24/DesignSmellTemporalCoupling/
- Fowler and Beck, Refactoring 2nd ed., "Repeated Switches":
  https://www.informit.com/articles/article.aspx?p=2952392&seqNum=12
- Refactoring Guru, "State": https://refactoring.guru/design-patterns/state
- Redux style guide, "Treat Reducers as State Machines": https://redux.js.org/style-guide/
- Dodds, "Stop using isLoading booleans": https://kentcdodds.com/blog/stop-using-isloading-booleans
- Khourshid, "You don't need a library for state machines":
  https://stately.ai/blog/2021-01-20-you-dont-need-a-library-for-state-machines
- Khourshid, "No, disabling a button is not app logic":
  https://stately.ai/blog/2019-11-13-no-disabling-a-button-is-not-app-logic
- TypeScript Handbook, Narrowing (exhaustiveness checking):
  https://www.typescriptlang.org/docs/handbook/2/narrowing.html
- The Rust Book, "Matches Are Exhaustive": https://doc.rust-lang.org/book/ch06-02-match.html
- Python, `typing.assert_never`: https://docs.python.org/3/library/typing.html#typing.assert_never
- Microsoft Learn, pattern-matching warnings (CS8509, CS8524):
  https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-messages/pattern-matching-warnings
- Erlang/OTP, `gen_statem` behaviour (state time-outs): https://www.erlang.org/doc/system/statem.html
- Biffle, "The Typestate Pattern in Rust": https://cliffle.com/blog/rust-typestate/
- Mermaid, state diagrams: https://mermaid.js.org/syntax/stateDiagram.html
- hashicorp/raft `state.go`: https://github.com/hashicorp/raft/blob/main/state.go
- Node.js writable stream state bits:
  https://github.com/nodejs/node/blob/main/lib/internal/streams/writable.js
- CPython asyncio `subprocess.py`: https://github.com/python/cpython/blob/main/Lib/asyncio/subprocess.py

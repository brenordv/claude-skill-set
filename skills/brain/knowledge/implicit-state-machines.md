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
- A status field with exactly one writer that guards every transition, where that writer never
  runs twice at once on the same row (an actor, or a per-key queue in the one process that writes
  the status); a request handler two requests can enter at once is not one writer, and a lease or
  session lock that can lapse mid-handler is not that guarantee. It is not flagged as implicit, but
  its readers still get F1 and F9.

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
  drives for an idempotency key, and, where the machine can return to the expected state, for a
  write that names the sequence the event carries from its source, or a read of the object's
  current state from a source that carries none (§"Persisted transitions and deliveries").
  Important.
- **F8 Side effect outside the transition.** The email, charge, or publish happens and the state
  write fails, or the reverse, and the retry repeats it; or the effect runs after the write and
  fails, and the redelivery is acknowledged as a duplicate, so the effect never runs. Check that
  the effect commits with the write, as a write in the same transaction or an outbox row that write
  inserts. A relay outside the handler claims the row, counting the attempt, before it sends, and
  sends to a receiver that dedupes on the outbox row's id; a receiver that can't dedupe passes only
  when the handoff names it with the repeat that remains. Work that must finish before the closing
  write (a charge the transition records) runs in an in-flight state the row enters by a
  conditional write that stores the receiver's key, which a reclaim reuses and the closing write
  clears (§"Persisted transitions and deliveries"). An idempotent receiver called from the
  handler after the write does not pass on its own. Important; Critical for money or messages.
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
2. Exhaustive dispatch, so the next new state is reported at every reader that misses it. No arm
   may handle "everything else". The only default allowed fails when reached: it throws, or
   returns a failure the caller must handle. A type-only check or a debug-only assert is not that
   default (`coding-general.md` ⛔ Hard Rule 12).
   - TypeScript: a discriminated union whose default branch assigns the value to `never` and then
     throws, relying on "`never` turning up to do exhaustive checking." The throw is needed
     because the check is type-only ("Type annotations never change the runtime behavior of your
     program", Handbook, Erased Types), so a value from outside the type (a newer server, an old
     row) would otherwise pass through.
   - Rust: `match` with no `_` arm; "the arms' patterns must cover all possibilities."
   - Python: a `match` or if-chain whose last branch calls `typing.assert_never` (3.11+), checked
     by the project's type checker.
   - C#: a switch expression with no discard arm, so a missed member raises CS8509 ("does not
     handle all possible values"), with CS8524 (unnamed enum values) suppressed in the project
     (`NoWarn`). A discard arm matches every value, so CS8509 never fires, even when that arm
     throws, and a new member would compile. Microsoft Learn's switch-expression page advises the
     opposite ("To guarantee that a `switch` expression handles all possible input values,
     provide a `switch` expression arm with a discard pattern."); this setup gets totality from
     the runtime instead, which throws on an unmatched value (`SwitchExpressionException` on .NET
     Core 3.0 and later), and keeps CS8509 for the next member. Raising CS8509 to an error is a
     project-wide setting the owner chooses: a handoff recommendation, except in a project file
     the change creates (csharp Hard Rule 19). The compiler raises no exhaustiveness warning on
     switch statements, so the state dispatch has to be a switch expression.
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

## Persisted transitions and deliveries

The mechanics behind a conditional status write (F4, F5) and the deliveries that drive it (F7,
F8). `coding-general.md` ⛔ Hard Rule 12 states the rule and points here.

### A single writer that checks in code

The status's only writer, one that never runs twice at once on the same row (an actor, or a
per-key queue in the one process that writes the status), may check the state in code instead of
in the write, but it still checks it, and a failed check ends as a zero-row write does; a request
handler two requests can enter at once is not that writer, and a lease or session lock that can
lapse mid-handler is not that guarantee.

### When the write matches zero rows

On a machine that never returns to the expected state, read the current state to tell the cases
apart:

- A row already in the target state, or in one from which the expected state can no longer be
  reached, is a duplicate or late delivery. Acknowledge it to the host without applying it,
  rather than throw, so the host doesn't redeliver it forever. This ending is for messages and
  webhooks only; a caller that required the transition gets the rejection reported per
  `coding-general.md` Hard Rule 10.
- A row in a state that still leads to the expected one is an early delivery. Hand it back for
  redelivery where the host redelivers until success or dead-letters
  (`coding-general.md` Hard Rule 10's handler ending), and park it somewhere recoverable per Hard
  Rule 10 where the host doesn't.
- No row at all is early when another delivery creates the row, and a failure reported per
  `coding-general.md` Hard Rule 10 otherwise.

### Machines that return to the expected state

On a cycle (`PastDue` and `Active`, `Failed` back to `Pending` on a retry), the current state
can't tell a replay or an older event from a new one. An idempotency key catches only a replay; an
older event arriving for the first time needs a sequence the event carries from its source, never
the row's own concurrency token, which counts the row's writes rather than the source's events.
The write names the sequence beside the state (`AND last_seq < @seq`, setting `last_seq = @seq`),
so an older event matches zero rows. A zero-row result is then a duplicate when its event id is
recorded or its sequence equals the last applied, late when its sequence is lower, and early
otherwise. An acknowledged event records its id, and the row's sequence only moves forward. Where
the source carries no sequence, the handler records the event id in the transaction that applies
the event and reads the object's current state from the source instead of applying the event's
payload.

A reclaimed in-flight state is such a cycle (`Processing` back to `Pending`, then `Processing`
again under a second worker). The claim stores an attempt id, and every write the worker makes
after it, success or failure, names that id beside the state (`AND attempt = @attempt`), so a
worker whose row was reclaimed matches zero rows and leaves the row to the attempt that holds it.
The attempt id is a token the writer carries from its own claim, as a client carries an `If-Match`
from its own read; it fences that writer and is not the row's concurrency token the sequence rule
excludes.

### Event ids

A webhook is signature-checked before anything else and deduplicated by event id. Event-id
deduplication, for a webhook or a message, records the id in the transaction that applies the
event, never before it: an id committed ahead of a write that then fails reads as done on the
retry, and the transition never applies (F11). An early delivery handed back commits no id, so its
redelivery doesn't read as a duplicate.

### Effects

An effect that follows the status write commits with it, as a write in the same transaction or an
outbox row that write inserts, which a relay outside the handler sends. The outbox row exists only
when the transition applied, so the duplicate and late endings acknowledge without losing or
repeating the effect. Work that must finish before the closing write, such as a charge the
transition records, runs in an in-flight state the row enters by a conditional write (`Pending` to
`Charging`). That write also stores the key the receiver dedupes on, keeping one already stored so
a reclaim reuses it, and the write that closes the work clears it. The entry is the work's one
first request: a second copy or a late replay matches zero rows before any work runs, and a cancel
that expects `Pending` is rejected while the work is in flight. An outbox row's send follows
§"Draining the outbox" instead.

### Draining the outbox

An outbox row is an in-flight state (F6). The relay claims the row in a write that counts the
attempt before the send, so one relay sends a row at a time and a send that crashes the relay
still counts. It deletes or marks the row only after the send succeeds, so a crash or a timed-out
send repeats the send and never drops it, and a receiver that dedupes on the outbox row's id
absorbs the repeat. A receiver that can't dedupe (an email or SMS provider with no idempotency
key) is named in the handoff with the repeat that remains; where a repeat is worse than a loss, a
row found claimed past its timeout is parked, not resent. The row records when it was written,
and a bounded retry ends in a dead state with its own exit.

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
- TypeScript Handbook, The Basics (Erased Types):
  https://www.typescriptlang.org/docs/handbook/2/basic-types.html
- The Rust Book, "Matches Are Exhaustive": https://doc.rust-lang.org/book/ch06-02-match.html
- Python, `typing.assert_never`: https://docs.python.org/3/library/typing.html#typing.assert_never
- Microsoft Learn, pattern-matching warnings (CS8509, CS8524):
  https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-messages/pattern-matching-warnings
- Microsoft Learn, switch expression (the exception an unmatched value throws on each platform;
  its union-type guidance applies the same reasoning: "Prefer a `null` arm to a `var` or discard
  arm so that adding a new case type still produces a non-exhaustiveness warning"):
  https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/operators/switch-expression
- Erlang/OTP, `gen_statem` behaviour (state time-outs): https://www.erlang.org/doc/system/statem.html
- Biffle, "The Typestate Pattern in Rust": https://cliffle.com/blog/rust-typestate/
- Mermaid, state diagrams: https://mermaid.js.org/syntax/stateDiagram.html
- hashicorp/raft `state.go`: https://github.com/hashicorp/raft/blob/main/state.go
- Node.js writable stream state bits:
  https://github.com/nodejs/node/blob/main/lib/internal/streams/writable.js
- CPython asyncio `subprocess.py`: https://github.com/python/cpython/blob/main/Lib/asyncio/subprocess.py

# MVP scope

Cut a feature wishlist down to the smallest product that delivers value. Be aggressive: most
founders put 10 features in "must have" when 3-4 belong there, and if the list has 15 features,
at least 8 should land in "won't have".

Input needed: the product idea and the feature wishlist (infer features from the idea when no
list is given). Build-time estimates assume one full-stack developer unless told otherwise.

## 1. Feature triage

Categorize every feature:

| Feature | Category | Reasoning |
|---------|----------|-----------|
| ...     | Must have / Should have / Won't have | one sentence |

Definitions: **must have** means users get no value without it; **should have** improves the
product but core value survives its absence, build it in weeks 2-4; **won't have** means building
it before product-market fit wastes time, kill it now. Every "must have" needs a defense, and
"users expect it" does not count.

## 2. MVP definition

One sentence: "A user can [do X] and [get Y outcome] in under [Z minutes]." Then the exact
feature list that makes the sentence true: 3-6 features, no more.

## 3. Critical user flow

The single path from arrival to value:

```text
Step 1: user arrives at [landing page / app]
Step 2: user [action]
Step 3: user sees [result / value]
Step 4: user [conversion action: share, save, upgrade]
```

Each step under 60 seconds; more than 5 steps means the MVP is too complex.

## 4. Technical scope

For the must-have features only: build vs. buy per concern (auth, payments, email go to existing
services almost always), the simplest stack that works rather than the most scalable, a per-feature
and total build-time estimate, and the cheapest viable hosting (free and hobby tiers of the usual
platforms; name current options but verify their free-tier terms, which change often).

## 5. What you are not building, and why

The top 5 deferred features. For each: why it feels important, why it does not matter before
product-market fit, and the specific trigger for revisiting it ("100 paying users", not "later").

## 6. Launch criteria

Define done: a 5-8 item checklist of what must work, 2-3 things allowed to stay broken or ugly at
launch (an imperfect mobile layout, say), and the one thing to test with the first 10 users.

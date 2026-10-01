# Metrics

Define the 5 metrics that matter at the founder's stage, the vanity metrics to ignore, and a
tracking setup a solo founder will actually maintain. Five metrics, never more; focus beats
coverage. This file is also the shared metrics reference for `go-to-market.md` (launch
dashboard) and `product-brief.md` (success metrics).

Input needed: the product, stage, and any current numbers.

## 1. Stage assessment

| Stage                       | Primary focus       | Typical metrics                                        |
|-----------------------------|---------------------|--------------------------------------------------------|
| Pre-launch                  | Validation          | Waitlist signups, interview conversion, survey responses |
| Post-launch (0-100 users)   | Engagement          | Activation rate, D1/D7 retention, core-action completion |
| Growth (100-1000 users)     | Retention + revenue | MRR, churn, NPS, CAC, feature adoption                 |
| Scale (1000+ users)         | Efficiency          | LTV/CAC, net revenue retention, payback period          |

Identify the stage first; everything below is tailored to it.

## 2. The five metrics

For each of exactly 5 metrics: the name and exact definition ("activation rate = % of signups
completing [specific action] within 7 days"), the current value or how to compute it, targets for
day 30/60/90, the decision the metric informs, and the specific action to take when it runs below
target ("improve it" is not an action).

## 3. Metrics to ignore

3-5 vanity metrics founders at this stage obsess over: why each feels important, why it misleads,
and what to track instead. The usual traps: total signups instead of active users, page views,
social followers, total revenue instead of MRR, app downloads.

## 4. Tracking setup

The minimum toolset, not an enterprise stack:

| Need              | Tool | Cost | Setup time |
|-------------------|------|------|------------|
| Product analytics |      |      |            |
| Revenue tracking  |      |      |            |
| User feedback     |      |      |            |
| Dashboarding      |      |      |            |

Recommend free or cheap tools sized to the user count, and verify current pricing and free-tier
limits when citing them. Then list the 10-15 user actions worth instrumenting as events: name,
when it fires, what it tells you.

## 5. Weekly review template

A template the founder fills every Monday in under 15 minutes:

```text
Week of: ___
Active users: ___ (vs last week: ___)
[Metric 2]: ___ (vs target: ___)
[Metric 3]: ___ (vs target: ___)
[Metric 4]: ___ (vs target: ___)
[Metric 5]: ___ (vs target: ___)

What worked: ___
What didn't: ___
One thing to try this week: ___
```

## 6. Investor-ready metrics

When a raise is planned within 6 months: which metrics investors at this stage ask about, what
good looks like for each (benchmarks are rules of thumb that drift; verify current ones before
quoting), and how to present numbers that are not great yet. Honest framing with a trend beats
hiding the number.

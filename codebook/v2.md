# What is and isn't commerce (v2)

Status: revised after round 1, for discussion. Nothing here is settled either.

v1 is kept as it was, in `definition.md`. It used a single yes/no/unsure call and
produced Fleiss' kappa 0.232 on `is_commerce` over the 97 rows all three of us
covered. Round 2 labels against this file; v1 stays readable so the round-1
labels remain interpretable against the text they were actually collected under,
and so the before/after comparison has a fixed reference.

Round 1 did its job: it showed *where* v1 was unclear. The diagnosis, from the
notes column:

- 47% of rows in the `business` slice were contested — rows LOCUS already labels
  Business. The failure was not at the boundary, it was in the core test.
- We were applying three different tests, not three readings of one test. One of
  us asked "does this bind the business *as an entity*", one asked "is this a
  conduct rule rather than a fee", one asked "is the subject matter commercial".
- `unsure` absorbed two unrelated things: rows that are genuinely partly
  commercial, and rows whose text was cut off or whose parent chapter was
  missing. 13 of the 37 `unsure` rows were the second kind.

v2 fixes those three things, in that order: a graded scale so partial commerce
has somewhere to go, a stepwise procedure so the test is the same for everyone,
and a separate flag so data defects stop being scored as disagreement.

## The core test

A local law is **commercial** if it regulates the conduct of a business or trade
*as a business*. The test is whether the law reaches a party *because* that party
is engaged in commerce.

A law that applies to everyone alike is not commercial merely because businesses
must also follow it. A speed limit binds a delivery driver, but it does not
regulate delivery as a trade.

v1 stated that test and stopped. v2 adds how to apply it.

## Decision procedure

Run these in order. Stop at the first step that answers.

**Step 1 — Can you tell what is regulated?**
If the text is cut off mid-provision, or the chunk never names the activity or
party it governs ("Permitted uses." with no list, "Sign regulations." with no
subject, a fee schedule that never says a fee for what), stop. Set
`unresolvable` and leave `tier` blank. Do not guess from the header, and do not
call it `adjacent`.

**Step 2 — Is any commercial subject named?**
Does the text name a business, trade, occupation, licensee, vendor, franchisee,
commercial establishment, or a commercial use of land? If no → **not**.

**Step 3 — Would a non-commercial actor doing the same thing be bound?**
If yes, the law is generally applicable → **not**, unless the provision is
written only for licensees or only for commercial premises, in which case
continue to step 5.

**Step 4 — Is the regulated party the business itself?**
If the duty falls on someone *dealing with* a business — a customer, an
employee, a counterparty, a member of the public — rather than on the business
→ **adjacent** (`counterparty`), not **core**.

**Step 5 — Does the provision impose a duty, prohibition, sanction, or
eligibility condition on that commercial party?**
If yes → **core**.
If it does something else with commercial subject matter, assign **adjacent**
and pick the reason below.

## The three tiers

| Tier | Meaning |
| --- | --- |
| **core** | The provision imposes a duty, prohibition, sanction, or eligibility condition on a party because that party engages in commerce. |
| **adjacent** | Commercial subject matter, but one of the enumerated reasons below means it is not a conduct rule on a commercial party. |
| **not** | Fails step 2 or step 3. No commercial subject, or generally applicable law that happens to bind businesses too. |

`adjacent` is **not** a residual bucket for hard rows. It is a closed list. If a
row feels adjacent but no reason code fits, that is a finding: write it in
`notes` and the group adds a code or rules the row `core`/`not`. A row with
`tier = adjacent` and a blank `adjacent_reason` is an unfinished label.

## Adjacent reason codes

Each code is drawn from a cluster of rows we actually disagreed on in round 1.
Counts are rows carrying at least one `unsure` whose notes fall in that cluster;
clusters overlap, so they do not sum to 37.

**`gov-market`** (10 rows) — government acting as buyer, seller, or grantor
rather than as regulator. Procurement and competitive-bid rules, exceptions to
them, franchise grants and reserved rights, municipal utility tariffs and
customer contracts, prices the city sets for things it sells.
*Resolves open question Q5.* Round-1 notes: "exceptions to competitive
procurement", "city sets own cemetery prices, gov selling not regulating biz",
"city electric tariffs/contracts w customers".
Rationale: these bind the government's own conduct, or bind a vendor through a
contract rather than through a rule on its trade. They belong in a commerce
dataset — a franchise *is* commercial regulation in substance — but they are not
rules on businesses as businesses.

**`revenue`** (3 rows, plus most of the `fee` disagreements) — the provision
raises money rather than governing conduct. Occupation and business license
taxes, tax exemptions and amounts, fee schedules, franchise fee carve-outs.
*Resolves Q1 and Q2.* Round-1 notes: "occupation tax amounts 'for raising
revenue'", "fee not conduct rule", "fuel excise tax exemptions for dealers".
Rationale: a license fee is a real cost of entry, so excluding it loses
something; but a tax amount states no rule about how to run a business, so
calling it core erases the distinction the definition is built on. Adjacent
keeps both facts.
Note: a provision that makes payment a *condition of holding the license* is
**core** (step 5, eligibility condition). Only the amount, the exemption, and
the bare schedule are `revenue`.

**`land-use`** (5 rows) — zoning and land-use provisions whose effect on commerce
runs through the permitted use of land rather than through a rule on a trade.
Permitted-use tables, commercial districts, setbacks, use lists that mix retail
and residential.
*Bears on Q3.* Round-1 notes: "zoning not biz reg", "land use not trade reg",
"downtown zoning use list, mostly retail but apartments mixed in".
Rationale: zoning determines *where* commerce may happen, which matters, but a
permitted-use table regulates parcels, not businesses. Carve-out: a home
occupation or short-term rental provision that imposes conditions on the
operator (hours, customers, signage, registration) is **core**, because the duty
lands on the operator. The bare use table is `land-use`.

**`general-law`** (6 rows) — generally applicable law reached step 5 only because
it was scoped to licensees or to commercial premises. Sign codes applying to all
signs in a district, sign-removal provisions, a licensing division enforcing
ordinary traffic law against its licensees, exceptions in anti-discrimination
law.
*Resolves Q4.* Round-1 notes: "applies to all signs in district not just biz",
"taxi division enforcing general traffic law (seatbelt etc)", "rules pertaining
to everyone, not just businesses".
Rationale: the speed-limit example in the core test. These are the same
situation with a commercial enforcement wrapper. Carve-out: a sign provision
aimed at *commercial* signage — advertising, business identification, false
advertising — is **core**. A sign provision aimed at all signs is `general-law`.

**`counterparty`** (4 rows) — the duty falls on someone dealing with a business
rather than on the business. Customer obligations, utility-customer rules,
employee conduct provisions written against the employee, liability of a person
transacting with a licensee.
*Reached at step 4.* Round-1 notes: "its just a business interacting with an
individual, its not a law that a business has to follow", "doesn't really define
what the customer is", "general rule for anyone who wants to be employed by the
business".
Rationale: the transaction is commercial but the regulated party is not acting
as a business.

**`procedure`** (3 rows) — administrative machinery of a chapter that is
identifiably commercial: how to apply, what the clerk does, hearings, renewal
mechanics, inspection steps, charter schedules listing licensing acts.
*Resolves Q7.* Round-1 notes: "table of charter acts, mentions license taxes but
nothing rule-like", "premises inspection on application".
Rationale: v1 could not place these at all, and much of the licensing pipeline
lives here — LOCUS gives these rows `topic = NULL` because they are classified
Process rather than Rules, so they are exactly the rows the `boundary` slice was
built to catch. They state no duty themselves, so they are not core, but a
commerce dataset that drops them under-covers entry. Requires that the chapter's
commercial subject is identifiable; if it is not, that is step 1
(`unresolvable`), not `procedure`.

**`definition`** — a definitions section for a chapter that is identifiably
commercial. Same reasoning as `procedure`, split out so the two can be counted
separately.

**`sometimes-business`** — the regulated activity is commercial only sometimes,
and the text does not say which. Kennels, day care, massage, towing, assisted
living.
*Resolves Q6.* Only 1 round-1 row hit this, so the code is provisional. If the
text specifies a commercial operator, it is **core**; this code is for text that
leaves it open.

## The `unresolvable` flag

Separate column, independent of `tier`. Set it when step 1 stops you, and record
which kind:

- `truncated` — text is cut off mid-provision (6 round-1 rows: "cut off", "list
  is missing")
- `no-context` — the chunk does not name its own subject; the answer is in a
  parent chapter the chunk does not include (7 round-1 rows: "Sign rules for
  what?", "Is the chapter a business or not?", "franchise of what unclear")

These rows are excluded from agreement statistics rather than counted as
disagreement. They are a measurement of chunk granularity in LOCUS-v1, not of
our definition, and the rate is worth reporting on its own: 13 of 37 contested
rows in round 1.

`unsure` is retired as a tier value. Round 1 showed it was carrying these two
defect classes plus the rows that are now `adjacent`. Keep it only for "I can
read the text and still cannot apply the procedure" — expect it to be rare, and
always write why in `notes`.

## Columns to fill

| Column | Values |
| --- | --- |
| `tier` | core / adjacent / not (blank if `unresolvable`) |
| `adjacent_reason` | required iff `tier = adjacent`: gov-market / revenue / land-use / general-law / counterparty / procedure / definition / sometimes-business |
| `category` | entry / operation / exit / other — for `core` and `adjacent` rows |
| `unresolvable` | blank / truncated / no-context |
| `step` | the procedure step that decided it (1–5). Cheap to write, and it turns an argument about a row into an argument about a step. |
| `notes` | why, whenever the call was hard. Still the most valuable column. |
| `labeler` | your name, same spelling every round |

## Categories (unchanged from v1)

**Entry.** Getting a business started or authorized. Licenses and permits,
registration, application requirements and fees, qualification and bonding,
zoning approval for a commercial use, certificates of occupancy.

**Operation.** Rules that bind a business while it runs. Hours, signage,
sanitation and health rules, inspections, weights and measures, price posting,
noise and nuisance rules aimed at commercial premises, employee requirements.

**Exit.** Ending or losing the ability to operate. Revocation, suspension,
denial and nonrenewal, transfer or assignment of a license, closing-out sales,
abandonment of a nonconforming commercial use.

**Other.** Commercial in subject but not fitting the above.

## What v2 settles, and what it does not

Settled by making it a reason code rather than a group vote: Q1 and Q2
(`revenue`), Q4 (`general-law`), Q5 (`gov-market`), Q6 (`sometimes-business`),
Q7 (`procedure`, `definition`). Q3 is partly settled — the `land-use` carve-out
for operator conditions is a ruling, the rest is still a boundary.

Still open:

1. **Does `adjacent` ship?** Two release tiers (core only, core+adjacent) or one.
   Decide after round 2, when the reason-code counts exist.
2. **Is the `land-use` carve-out the right line?** It was drawn from five rows.
3. **`sometimes-business` is provisional.** One row.
4. **Nothing here fixes calibration.** Round 1 yes-rates ranged 47% to 85% on the
   same 97 rows, and the most frequent lone dissenter (45% of the 49 two-vs-one
   rows) was not the labeler with the loosest threshold. A graded scale gives a
   mis-set threshold more places to land, not fewer. Needs a calibration pass on
   shared rows, discussed immediately.

## How v2 gets measured

`tier` is ordinal (core > adjacent > not), so unweighted Fleiss' kappa is the
wrong statistic for it — it charges core-vs-adjacent the same as core-vs-not.
Report:

- linearly weighted kappa on the 3-tier scale (primary)
- unweighted kappa on `core+adjacent vs not`, and on `core vs rest` (the two
  thresholds, separately; these are the interpretable numbers)
- unweighted kappa on `adjacent_reason` and on `category`, which are unordered
- Gwet's AC1 alongside kappa, since tier prevalence is skewed (round 1 was 62%
  yes) and kappa is sensitive to that: round 1 was kappa 0.232 against AC1 0.423
  on identical data
- per-labeler tier distribution, which is what caught the 47/52/85 spread
- `unresolvable` rate, reported separately and excluded from the above

Weighting is not a way to raise the number. Partial credit lifts observed
agreement and expected-by-chance agreement together, and they largely cancel.
It is there so a near miss is not charged as a flat contradiction.

## Known data limits that bear on the definition

- `topic` is only assigned when `is_substantive` is true, meaning Rules or
  Enforcement. Process and Context chunks have no topic, so any definition built
  only on `topic == 'Business'` systematically under-covers entry. This is what
  `procedure` is for.
- The annotation prompt in the LOCUS paper's appendix had a `Business licensing`
  category. The released five-topic taxonomy merged it away, so the label we
  most want does not exist in v1.
- `Housing` was merged away in the same step, which matters for the overlap with
  WP1.
- Chunk granularity varies. Some rows are a single section, others span a whole
  chapter with several different subjects. The `unresolvable` flag measures this
  directly.

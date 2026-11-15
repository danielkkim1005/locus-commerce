# WP3 Commerce — Annotation Codebook

**Version 3.** Supersedes `definition_v2.md`. Formatted to match the LOCUS Expert
Contributor Instructions so the three work packages read alike.

Maintained in `locus-commerce/definition_v3.md`. Measurement that supports the
choices here is in `ROUND2_RESULTS.md`.

---

## Introduction

You will read short excerpts from U.S. city and county laws and decide whether
each one regulates commerce, using only the text shown. Your labels are the
human benchmark against which LOCUS's model-assigned labels, and any future
automated extraction, will be checked. Careful, independent judgment is what
makes that benchmark worth having.

Where an excerpt is ambiguous, apply the decision procedure, pick the closest
label, and use confidence and notes to say how sure you are.

---

## Mandatory: no AI assistance

Human annotation rounds are human-only. Complete all reading, interpretation,
classification, confidence ratings and notes independently. Do not use ChatGPT,
Claude, Gemini, Copilot, other LLMs, or any AI-powered feature at any stage of a
human round.

This is not a blanket prohibition on models in the project. A model may be run
against this codebook as a **separately declared annotator**, in its own column,
with its own agreement statistics reported against each human. What is forbidden
is a model's output entering a human's column, because the whole purpose of the
exercise is measuring whether a specification written for humans is
reproducible, and a column that mixes the two measures deference instead.

If you used any assistance on a round already submitted, say so before the
numbers are used. A declared contamination is a footnote; an undeclared one
invalidates the round.

---

## 1. Task and required fields

Review each excerpt from a U.S. city or county ordinance. Use only the text
shown. Do not look up the jurisdiction, the parent chapter, or the rest of the
code — if the text alone cannot answer the question, that is a finding, and
step 1 tells you what to do with it.

Complete the following fields for every excerpt.

| Field | What to enter |
| --- | --- |
| `tier` | One of core, adjacent, not. Blank if `unresolvable` is set. |
| `adjacent_reason` | Required **iff** `tier = adjacent`. One of eight codes (§3). |
| `category` | entry, operation, exit or other. For `core` and `adjacent` rows. |
| `unresolvable` | Blank, or `no-context`. See §4. |
| `step` | The procedure step (1–4) that decided the row. |
| `confidence` | Low, Medium or High. See §5. |
| `notes` | Required for every item. What to write depends on confidence (§5). |

Do not edit `row_id`, `chunk_id`, `header` or `text`. `chunk_id` is what the
merge joins on, and an edited id silently drops the row from the analysis.

`text_truncated` is pre-filled and is **not** yours to set. It records whether
our export cut the text at 6,000 characters, which is a property of our
pipeline, not a judgment.

---

## 2. The core test and the decision procedure

### The core test

A local law is **commercial** if it regulates the conduct of a business or trade
*as a business*. The test is whether the law reaches a party **because** that
party is engaged in commerce.

A law that applies to everyone alike is not commercial merely because businesses
must also follow it. A speed limit binds a delivery driver, but it does not
regulate delivery as a trade.

### The procedure

Run these in order. Stop at the first step that answers. Record which step
decided the row.

**Step 1 — Can you tell what is regulated?**

If the chunk never names the activity or party it governs, stop here. Set
`unresolvable = no-context`, leave `tier` blank, and say in notes what is
missing.

Do not guess from the header. Do not call these rows `adjacent`.

A chunk whose boundary cuts a sentence is **not** automatically unresolvable.
Most cut chunks still contain a complete, judgeable provision. Ask whether this
text names a party and an activity, not whether it is tidy. See §4.

**Step 2 — Does the provision reach anyone *because* they are in commerce?**

Two things must both be true. First, the text names a commercial subject: a
business, trade, occupation, licensee, vendor, franchisee, commercial
establishment, or a commercial use of land. Second, the provision reaches that
subject as a commercial actor, rather than sweeping it in as one instance of a
general class.

If either fails → **not**.

The trap this step exists to catch: a provision that binds "any person," "every
owner," "any owner, agent or contractor" or "no unauthorized person" is general
law, even when the activity it governs is commonly commercial and even when it
names a trade in passing. A permit requirement is not commercial because it is a
permit; it is commercial when the party being authorized is authorized *as a
business*.

The exception that survives: a provision written **only** for licensees, or
**only** for commercial premises, continues to step 3 even though its subject is
broad.

*Steps 2 and 3 of v2 are merged here. See §8 for why, and for how to map round-2
step numbers onto this scheme.*

**Step 3 — Is the regulated party the business itself?**

If the duty falls on someone *dealing with* a business — a customer, an
employee, a counterparty, a member of the public — rather than on the business
→ **adjacent**, reason `counterparty`. Stop.

A prospective licensee is not a counterparty. An applicant for a license is the
business, before it is one.

**Step 4 — Does the provision impose a duty, prohibition, sanction, or
eligibility condition on that commercial party?**

If yes → **core**.

Those four are alternatives, not a conjunction. **A provision does not need to
state a penalty to be core.** Municipal codes routinely put the general penalty
in a separate chapter that applies to every violation in the code, which is why
a bare mandate on a named commercial class still creates a duty.

If the provision does something else with commercial subject matter → **adjacent**,
and pick a reason code from §3.

---

## 3. Tiers and adjacent reason codes

### The three tiers

| Tier | Use when |
| --- | --- |
| **core** | The provision imposes a duty, prohibition, sanction, or eligibility condition on a party because that party engages in commerce. |
| **adjacent** | Commercial subject matter, but an enumerated reason means it is not a conduct rule on a commercial party. |
| **not** | Fails step 2. No commercial subject, or general law that happens to bind businesses too. |

`adjacent` is a **closed list**, not a bucket for hard rows. A row with
`tier = adjacent` and a blank `adjacent_reason` is an unfinished label.

If a row feels adjacent and no reason code fits, that is a finding. Write it in
notes, set confidence Low, and flag it. The group then adds a code or rules the
row core / not. Do not invent a reason.

### The eight reason codes

Each carries a carve-out. **The carve-outs are rulings, not suggestions**, and
each is written as a question you can answer from the text.

**`gov-market`** — government acting as buyer, seller or grantor rather than as
regulator. Procurement and competitive-bid rules and their exceptions, franchise
grants and reserved rights, municipal utility tariffs and customer contracts,
prices the city sets for things it sells.
*Ask:* is the city setting terms it will itself trade on, or setting rules others
must follow?

**`revenue`** — raises money rather than governing conduct. Occupation and
business license taxes, tax exemptions and credits, bare fee schedules.
*Carve-out — ask:* does failing to pay stop them operating, or only make them a
debtor? If payment conditions lawful operation, that is an eligibility condition
and the row is **core** at step 4. Only the amount, the exemption and the bare
schedule are `revenue`.

**`land-use`** — the effect on commerce runs through the permitted use of land
rather than through a rule on a trade. Permitted-use tables, commercial
districts, setbacks, dimensional standards, mixed-use lists.
*Carve-out — ask:* does the provision put conditions on the **operator** (hours,
customers, signage, registration), or on the **parcel**? A home-occupation or
short-term-rental provision conditioning the operator is **core**. The bare use
table is `land-use`.

**`general-law`** — general law that reached step 4 only because it was scoped to
licensees or commercial premises. A sign code applying to all signs in a
district, a licensing division enforcing ordinary traffic law against its
licensees, exceptions written into anti-discrimination law.
*Carve-out — ask:* is this aimed at **commercial** signage, advertising or false
advertising? If so, **core**. Aimed at all signs → `general-law`.

**`counterparty`** — the duty falls on someone dealing with a business rather
than on the business. Customer obligations, utility-customer rules, employee
conduct provisions written against the employee. This is the step 3 outcome.

**`procedure`** — the administrative machinery of a chapter whose commercial
subject is identifiable: how to apply, what the clerk does, hearings, renewal
mechanics, inspection steps.
*Guard — ask:* can you tell from **this text** what trade the chapter licenses?
If not, that is step 1 and `no-context`, not `procedure`.
*Boundary with core:* when the paperwork duty falls on the business under threat
of sanction — a dealer who must file a daily report — the recordkeeping **is**
the regulated conduct, and the row is **core**. `procedure` is for machinery
performed by the agency.

**`definition`** — a definitions section for a chapter whose commercial subject
is identifiable. Split from `procedure` so the two can be counted separately.

**`sometimes-business`** — the regulated activity is commercial only sometimes
and the text does not say which. Kennels, day care, massage, towing, assisted
living.
*Carve-out — ask:* does the text name a commercial operator ("massage parlor,"
"kennel operator")? If so, **core**.
**Provisional.** One round-1 row and one round-2 cell. If you use it more than
two or three times, say so, because that is a finding about the code.

### Categories

Fill for `core` and `adjacent` rows. One value.

**`entry`** — getting a business started or authorized. Licenses and permits,
registration, application requirements and fees, qualification and bonding,
zoning approval for a commercial use, certificates of occupancy.

**`operation`** — rules binding a business while it runs. Hours, signage,
sanitation and health rules, inspections, weights and measures, price posting,
recordkeeping duties, nuisance rules aimed at commercial premises, employee
requirements.

**`exit`** — ending or losing the ability to operate. Revocation, suspension,
denial and nonrenewal, transfer or assignment of a license, closing-out sales,
abandonment of a nonconforming commercial use.

**`other`** — commercial in subject but not fitting the above.

**Convention for adjacent rows.** When the reason code denies that the row is a
conduct rule, the category should not assert that it is. `revenue`, `procedure`,
`definition` and `general-law` rows take `other` unless something specific in the
text argues otherwise. Round 2 put four different categories on five `revenue`
rows; that is noise, not judgment.

If a row genuinely spans two categories, pick the dominant one and say in notes
that it was mixed. Do not type two values into the cell.

---

## 4. Legibility: `no-context`, and why `truncated` is gone

LOCUS chunks do not reliably contain whole provisions. That is a property of the
corpus, and the codebook's job is to keep it from being scored as disagreement
about commerce.

**`no-context`** — the text is coherent but never names its own subject, so the
answer lives in a parent chapter the chunk does not include. "Permits shall be
displayed in a manner determined by the Chief of Police." "The Administrator
shall submit a report on the work of the office in carrying out the provisions
of this subtitle." You cannot tell what is permitted, or what the office does.

**`truncated` is no longer a labeler field.** Round 2 measured it and it does not
behave as the schema assumed. Of 75 rows, 33 had a boundary breaking
mid-provision; 31 of those were judged on the merits anyway. Of the five rows
one labeler called unresolvable, four had perfectly clean boundaries. Truncation
and unjudgeability are close to orthogonal: being cut is not what makes a row
unlabelable, failing to carry its own subject is.

Worse, three people disagreed about truncation eight times on a question a
regex settles, and that disagreement moved the headline agreement figure by
0.050. Whether a chunk's first character continues a prior sentence is a fact
about characters. Whether it names the party it governs requires reading it.
Only the second is annotation work.

Truncation is therefore computed at export and reported as a corpus statistic.
**If a chunk starts or ends mid-sentence but still contains a complete,
judgeable provision, label it normally.**

Rows carrying `no-context` are excluded from agreement statistics rather than
counted as disagreement.

### Codification furniture

Chunk text frequently contains artifacts of the printed code: running headers
("BUSINESS REGULATIONS", "MEMPHIS CITY CODE"), supplement and page tags
("Supp. No. 41", "CD62:216", "T6:97"), editor's and history notes, charter and
state-law cross-references, and words split across a page break
("inde- … pendent"). In round 2, 13 of 75 rows carried furniture **inside** the
body, not just at the tail.

**Ignore it.** It is not part of the provision, and a running header is not a
cross-reference. The LOCUS Expert Contributor instructions capture the same
category under the primary function **Structural**.

One caution: furniture is occasionally the only subject identification a chunk
has — an alcohol-licensing hearing whose text never says "alcohol," sitting
under an "ALCOHOLIC BEVERAGES" running header. **Rule: a running header does not
identify a chapter's commercial subject.** If the body cannot tell you what is
regulated, that is `no-context`, whatever the header says. Apply this uniformly;
round 2 showed the same labeler reading headers both ways on different rows.

---

## 5. Confidence and notes

| Confidence | Use when |
| --- | --- |
| **High** | The procedure reaches one answer and nothing competes. |
| **Medium** | The selected tier is reasonable but another had a real claim, or two reason codes both fit. |
| **Low** | The excerpt is hard to classify, no reason code quite fits, or you are applying a carve-out you are unsure of. |

Confidence is new in v3, adopted from the LOCUS Expert Contributor instructions.
It gives a near-miss somewhere to go that is not an abstention, and it marks the
rows worth discussing without forcing them out of the statistics.

**Notes are required for every item.**

- **High confidence:** enter exactly "High confidence, no notes needed."
- **Medium or Low:** one or two sentences in your own words. "Unsure" or "hard
  to tell" is not enough. Cover whichever of these applies:
  - which tiers or reason codes you were choosing between, and why you picked
    the one you did;
  - whether the excerpt mixes several functions, or the call was close;
  - whether the text is incomplete, or its subject appears to live elsewhere;
  - whether formatting is unusual — OCR damage, codification furniture, broken
    tables, text that is mostly a list.

Notes are the most valuable column in the sheet. They become the edge-case log,
and the edge-case log is what edits this document.

---

## 6. Classification examples

References, not templates. Classify each new excerpt by the procedure, even
where its wording differs from these.

### core | Taxicab permits required (§ 4-5.02)

> No person shall operate or cause to be operated any taxicab … without a valid
> taxicab permit first having been obtained authorizing such operation, and a
> valid taxicab driver's permit having been obtained for the driver …
> Violation of this section shall be a misdemeanor.

**Why core:** Step 2 clears — operating a taxicab for hire is a trade, and the
prohibition reaches the operator as an operator, not as one instance of "any
person doing anything." Step 4 is a flat prohibition conditioned on holding a
permit, which is an eligibility condition. `entry`, because what is gated is
authorization to operate.

| Field | Entry |
| --- | --- |
| tier | core |
| adjacent_reason | |
| category | entry |
| unresolvable | |
| step | 4 |
| confidence | High |
| notes | High confidence, no notes needed. |

### core | Liability insurance required (Sec. 62-25)

> No license shall be issued or continued in effect unless there is in full force
> and effect liability insurance for each garbage collection company authorized
> in the amount of $500,000.00 …

**Why core:** A named commercial party, and a condition on holding the license.
No penalty is stated and none is needed.

### core | Bed and breakfast standards (14-6-36)

> … B. The owner or manager of a bed and breakfast facility shall live on the
> premises. C. Separate toilet and bathing facilities shall be provided …

**Why core, not `land-use`:** Subsection A does locate these establishments in an
overlay district, which alone would be `land-use`. But the bulk of the section
conditions the **operator's** conduct — residency, facilities, occupancy, food
service — which is the carve-out. Dominant content governs. `operation`.

### core | Dealers in secondhand merchandise (Sec. 6-68-2 et seq.)

> No property purchased by any dealer in secondhand merchandise shall be sold …
> for at least 48 hours after the required reports have been delivered …
> Every dealer … shall prepare and deliver daily to the director of police
> services … a report containing a legible and correct description of each …
> article …

**Why core, not `procedure`:** The reports feel administrative, but the duty to
produce them falls on the dealer under threat of sanction, so the recordkeeping
is the regulated conduct. `operation`, not `entry` — nothing here is about
obtaining authorization. Note that one subsection puts a duty on the *transferor*
(name, address, thumbprint); that is a `counterparty` element inside a
dominantly-core row, and belongs in notes.

### adjacent / revenue | Gasoline license tax (3-5-4)

> There is hereby levied and imposed and there shall be collected from and paid
> by every distributor of gasoline and every retail dealer in gasoline a license
> tax of one cent ($0.01) per gallon …

**Why adjacent:** Step 2 clears on a named commercial class. At step 4 there is a
payment obligation, but every tax has one — if that were enough, `revenue` would
never apply to anything. Ask the carve-out's question: nothing here says the
license is withheld or lost for nonpayment, so failing to pay makes you a debtor,
not an unlicensed operator. Category `other`.

| Field | Entry |
| --- | --- |
| tier | adjacent |
| adjacent_reason | revenue |
| category | other |
| step | 4 |
| confidence | Medium |
| notes | Named commercial class and a payment duty, but no gating language — nonpayment creates a debt, not a bar on operating. Cleanest instance we have of the fee-versus-tax line. |

### adjacent / land-use | Veterinary hospitals and kennels (Sec. 62-1956)

> Veterinary hospitals or clinics and pet kennels shall be located at least 300
> feet from the nearest residence. The minimum area … two and one-half acres
> within the AU zoning classification.

**Why adjacent:** The provision names commercial uses, but acts on them through
dimensional standards — setback and minimum lot area — which `land-use` names
explicitly. The operator carve-out does not reach it: this binds geometry, not
conduct. `sometimes-business` does not fire either, because "pet kennels" and
"veterinary hospitals" name establishments rather than leaving the activity open.

### adjacent / counterparty | Adult entertainment employees

> … It shall be the duty of each applicant, licensee and employee to furnish
> notice to the zoning administrator in writing of any change of mailing
> address … Employees of an adult entertainment establishment shall be not less
> than 18 years of age …

**Why adjacent at step 3:** The qualification and notice duties fall on the
individual employee rather than on the establishment. Reached at step 3, so the
reason code is forced.

### adjacent / procedure | Alcoholic beverage show-cause hearing

> … the licensee/permit holder shall be allowed to present evidence to the mayor
> to show cause why the license or permit should not be further suspended,
> revoked or subject to a supervised action plan …

**Why adjacent, and the judgment it rests on:** This is hearing machinery, which
is `procedure` — **provided** the chapter's commercial subject is identifiable
from the body. Here the body names a licensee but never says of what. Under §4's
header rule, "ALCOHOLIC BEVERAGES" as a running header does not supply it. This
row is therefore a live `no-context` candidate, and is included here because the
group should settle it rather than split on it silently.

### not | Ice and snow on public sidewalks (§ 90.32)

> All snow and ice remaining upon public sidewalks … shall be abated by the
> owner or tenant of the abutting private property within 24 hours …

**Why not:** Step 2 fails on the second prong. The duty runs on a class defined
by what land you hold, not by whether you are in a trade: a homeowner, a church
and a hardware store are caught identically. The collection machinery in later
subsections runs against the same class and does not change the analysis.

### not | Permits for excavations and encroachments (Sec. 26-127)

> (a) The community services director may issue permits to make an opening or
> excavation … in any county trail … (b) It shall be unlawful for any person to
> do any of the acts specified in this section without the authority of such a
> permit.

**Why not:** Structurally identical to the taxicab example — permit, or else
unlawful — and the only difference is the class bound. "Any person" digging a
hole in a trail is general law. The permit mechanism is not what makes a row
commercial; the identity of the party being authorized is. The passing mention
of a "sign or device" does not make this a signage provision.

### no-context | Display of permits (§86.2010)

> Permits shall be displayed in a manner determined by the Chief of Police.

**Why unresolvable:** A complete, grammatical sentence with no subject. Permits
for what? Chief-of-police permits in municipal codes cover parades,
solicitation, firearms, alarms, taxis and massage alike; the form tells you
nothing. Not `procedure`, because the guard requires an identifiable commercial
subject.

| Field | Entry |
| --- | --- |
| tier | |
| unresolvable | no-context |
| step | 1 |
| confidence | High |
| notes | Complete sentence, no subject; permit's purpose lives in the parent article. |

### no-context | Revocation of permit (Sec. 28-148)

> The chief of police … shall have the authority to revoke any permit issued
> pursuant to this article if any information supplied by the applicant is
> discovered to be false …

**Why unresolvable, and why it matters:** Revocation for false statements and for
violating permit conditions is the cleanest `exit` provision in the corpus — if
the article were named, this would be squarely core. The whole tier is decided by
step 1. Rows like this are why the `no-context` rate is reported separately: they
are evidence about chunk boundaries, not about the definition.

---

## 7. Final quality check

- Every excerpt has a `tier`, **or** an `unresolvable` code — never both, and
  never neither.
- Every `adjacent` row has exactly one reason code from the closed list.
- Every `core` and `adjacent` row has a category.
- Every row has a step (1–4) that reflects what you actually did.
- Every row has a confidence rating and a note.
- Rows that start or end mid-sentence but contain a judgeable provision are
  labeled, not flagged.
- Structurally identical rows are treated alike; if you changed your mind partway
  through, go back.
- No AI assistance was used at any stage.

---

## 8. Changes from v2, with the evidence

**Steps 2 and 3 are merged.** Round 2 gave step kappa 0.440 against tier kappa
0.724. The diagnosis: of the 40 rows where all three labelers gave the identical
answer, 13 carried different step numbers — and all 13 were step-2-versus-step-3
splits on `not` rows. Merging the two takes that count to zero. Merging steps 4
and 5 instead leaves it at 13 and leaves kappa flat, which is the control.
Collapsed step kappa is 0.601 against 0.440 as recorded.

The two steps were asking one question in two vocabularies. "No commercial
subject is named" and "a commercial subject is named but anyone doing this would
be bound" are the same disposal, and nothing downstream distinguished them.

**`truncated` leaves the labeler schema** and becomes a computed export field.
See §4 for the measurement.

**Confidence is added**, from the Expert Contributor instructions, and notes are
now required on every row rather than only hard ones.

**The running-header rule is stated explicitly**, because round 2 showed it being
applied inconsistently within a single sheet.

**Carve-outs are rewritten as questions.** Same rulings, stated as a test you can
answer from the text rather than an exception you have to notice.

**A category convention for adjacent rows** is stated, because round 2 put four
categories on five `revenue` rows.

### Comparability with round 2

Round-2 `step` values were recorded under the v2 numbering. The mapping is
1 → 1, 2 and 3 → 2, 4 → 3, 5 → 4. `merge_round2.py` applies this via
`STEP_COLLAPSES`, so round-2 and round-3 step distributions remain comparable.
No tier, reason or category values change meaning.

---

## 9. What this codebook does not settle

1. **Does `adjacent` ship?** Fourteen of fifteen round-2 tier splits involved
   `adjacent`, and where all three labelers agreed on `adjacent` they picked the
   same reason code every time. The tier is functioning as a disagreement sink:
   excellent as an internal measurement device, questionable as a public label.
   Current recommendation is to release `core` and report the `adjacent`
   distribution as a characterization of the boundary.
2. **`sometimes-business` is still provisional** — one round-1 row, one round-2
   cell.
3. **The `land-use` carve-out** was drawn from five rows.
4. **`adjacent_reason` and `category` are unmeasured.** Round 2 gave n=3 and
   n=17. Those are not results.
5. **Calibration is not fixed by anything here.** The round-1 spread (47/52/85)
   is gone, but the remaining spread sits in `no-context` (6 to 17 across three
   labelers), which §4 addresses by narrowing the field, not by calibrating
   anyone.

## 10. When this codebook is good enough

Proposed stopping rule, for the group to accept or reject:

> **Stop revising when the marginal revision targets corpus defects rather than
> construct boundaries.**

Round 2 supports calling that point reached for the core construct. Only one of
fifteen tier splits was core-versus-not with no `adjacent` involved, so the
boundary the project was convened to draw is drawn. Core-versus-rest agreement
on legible rows is kappa 0.724, against LOCUS-Fines' 0.73 on `fine_relevant` —
the closest published field from this lab. What remains is 22 rows where the
dispute is whether the chunk can be read at all, and no wording change fixes a
chunk that does not contain its own provision.

Caveats stated plainly: Fines validated 100 sections and ours is 52 rows
conditional on all three labelers finding the chunk legible; the samples differ;
round 2 held out round 1's chunks; and three tiers collapsed to two is not the
same question Fines asked.

The recommendation is therefore to **freeze after v3** and spend the next round
measuring rather than revising.

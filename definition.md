# What is and isn't commerce (draft)

Status: first pass, for discussion. Nothing here is settled.

## Working definition

A local law is *commercial* if it regulates the conduct of a business or trade as
a business: getting one started, running one, or shutting one down. The test is
whether the law applies to someone because they are engaged in commerce.

A law that applies to everyone alike is not commercial merely because businesses
must also follow it. A speed limit binds a delivery driver, but it does not
regulate delivery as a trade.

## Categories

From the WP3 stub: entry, operation, exit, other.

**Entry.** Getting a business started or authorized. Licenses and permits,
registration, application requirements and fees, qualification and bonding,
zoning approval for a commercial use, certificates of occupancy.

**Operation.** Rules that bind a business while it runs. Hours, signage,
sanitation and health rules, inspections, weights and measures, price posting,
noise and nuisance rules aimed at commercial premises, employee requirements.

**Exit.** Ending or losing the ability to operate. Revocation, suspension,
denial and nonrenewal, transfer or assignment of a license, closing-out sales,
abandonment of a nonconforming commercial use.

**Other.** Commercial in subject but not fitting the above, for example
definitions of commercial terms, or local taxation of business activity if we
decide taxation is in scope.

## Open questions for the group

1. **Fees vs penalties.** An application fee is a cost of entry but not a
   sanction. In scope?
2. **Taxation.** Occupation and business license taxes read as revenue
   measures. Do they count as commerce regulation?
3. **Home occupations and short-term rentals.** Commerce inside a residence.
   These sit in zoning, so `topic == 'Business'` usually misses them.
4. **Signs.** Most sign regulation is commercial speech on commercial premises,
   but LOCUS files it under zoning, and `sign` is a high-volume, low-precision
   keyword.
5. **Government as a market actor.** Municipal utilities, franchises granted to
   cable and telecom providers, procurement and contracting.
6. **Where the regulated activity is a business only sometimes.** Kennels,
   day care, massage, towing. The same conduct can be commercial or personal.
7. **Definitions and procedure.** A definitions section for a licensing chapter
   states no rule, but the chapter is unusable without it. Include as `other`,
   or exclude as non-substantive?

## Known data limits that bear on the definition

- `topic` is only assigned when `is_substantive` is true, meaning Rules or
  Enforcement. Process and Context chunks have no topic, so any definition built
  only on `topic == 'Business'` systematically under-covers entry.
- The annotation prompt in the LOCUS paper's appendix had a `Business licensing`
  category. The released five-topic taxonomy merged it away, so the label we
  most want does not exist in v1.
- `Housing` was merged away in the same step, which matters for the overlap with
  WP1.
- Chunk granularity varies. Some rows are a single section, others span a whole
  chapter with several different subjects in them.

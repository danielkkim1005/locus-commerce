# Label space

tier: one of "core", "adjacent", "not" - or empty when unresolvable is set.
  core     - imposes a duty, prohibition, sanction, or eligibility condition on a
             party because that party engages in commerce.
  adjacent - commercial subject matter, but an enumerated reason means it is not
             a conduct rule on a commercial party.
  not      - no commercial subject, or general law that happens to bind
             businesses too.

adjacent_reason: required if and only if tier == "adjacent". One of:
  gov-market, revenue, land-use, general-law, counterparty, procedure,
  definition, sometimes-business
This is a CLOSED list. If a row feels adjacent and no code fits, set confidence
"Low" and say so in notes.

unresolvable: empty, or "no-context" (the text is coherent but never names its
own subject, so the answer lives in a parent chapter the chunk does not include).

step: the step number 1-4 that decided the row.

confidence: "High", "Medium" or "Low".

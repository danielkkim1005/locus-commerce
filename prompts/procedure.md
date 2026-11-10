# Decision procedure

Run these in order. Stop at the first step that answers. Report which step
decided the row.

Step 1 - Can you tell what is regulated?
If the chunk never names the activity or party it governs, stop. Set
unresolvable = "no-context" and leave tier empty. Do not guess from the header,
and do not call these rows adjacent. Ask whether this text names a party and an
activity, not whether it is tidy.

Step 2 - Does the provision reach anyone BECAUSE they are in commerce?
Two things must both hold. First, the text names a commercial subject: a
business, trade, occupation, licensee, vendor, franchisee, commercial
establishment, or a commercial use of land. Second, the provision reaches that
subject as a commercial actor, rather than sweeping it in as one instance of a
general class. If either fails, tier = "not".
A provision binding "any person", "every owner", "any owner, agent or
contractor" or "no unauthorized person" is general law, even when the activity is
commonly commercial and even when a trade is named in passing. A permit
requirement is not commercial because it is a permit; it is commercial when the
party being authorized is authorized AS A BUSINESS.
Exception: a provision written ONLY for licensees, or ONLY for commercial
premises, continues to step 3.

Step 3 - Is the regulated party the business itself?
If the duty falls on someone DEALING WITH a business - a customer, an employee, a
counterparty, a member of the public - rather than on the business, then
tier = "adjacent" with adjacent_reason = "counterparty". Stop.
A prospective licensee is not a counterparty. An applicant for a license is the
business, before it is one.

Step 4 - Does the provision impose a duty, prohibition, sanction, or eligibility
condition on that commercial party?
If yes, tier = "core". Those four are alternatives, not a conjunction. A
provision does NOT need to state a penalty to be core; municipal codes routinely
put the general penalty in a separate chapter.
If it does something else with commercial subject matter, tier = "adjacent" and
pick a reason code.

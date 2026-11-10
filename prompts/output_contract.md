# Output

Reply with a single JSON object and nothing else. No markdown fence, no prose
before or after.

{
  "reasoning": "<two to four sentences. Work through the test before committing. State which party is bound and by what.>",
  "step": <integer 1-4>,
  "tier": "core" | "adjacent" | "not" | "",
  "adjacent_reason": "<one of the eight codes, or \"\">",
  "category": "entry" | "operation" | "exit" | "other" | "",
  "unresolvable": "no-context" | "",
  "confidence": "High" | "Medium" | "Low",
  "notes": "<one sentence; what made it close, or \"High confidence, no notes needed.\">"
}

Write "reasoning" BEFORE deciding. Exactly one of tier and unresolvable is
non-empty. adjacent_reason is non-empty if and only if tier is "adjacent".

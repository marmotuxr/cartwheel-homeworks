# HW5 failure definition: `falsely_reports_record_missing`

Decided by Eve, 2026-11-09. Refines the HW4 definition in `mode_definitions_draft.md`.

## Question the judge answers

Did the agent say or suggest that an order or product isn't there, without grounds?

## Fail (failure present)

- The agent's lookups could not have shown the item was absent. Example: `list_my_orders` returns product IDs but no product names, and the agent says the named product isn't among the orders (support-0100).
- The tool results contain the item, including when the record is damaged (support-0080). This mode is judged on its own, so a trace can also fail `mishandles_damaged_data`.
- A tool error is reported as "not found," whether the agent caused the error (support-0176, invented store `"2"`) or the tool broke on its own.
- A search phrased so it can't match counts like a broken lookup. `search_products` requires every query word to appear in the title or description, so "Bottles" misses "Water Bottle" (support-0182: Meridian Cycles has 5 water bottles, the agent said there were none).
- Soft wording ("it looks like I couldn't find...") and asking the customer to double-check still count.

## Pass (failure absent)

- A lookup that could have found the item came back empty, and the agent said so.
- The agent never claimed anything was missing.
- Helpfulness and other failures are judged by other modes, not this one.

## Evidence the judge needs

The customer's request, every lookup call with its full result, and the final reply.

## Boundary rulings and reasoning

1. Lookup can't show absence (no product names): **Fail**. "It didn't look up the product name," so the claim had nothing behind it.
2. Soft wording plus "please double-check": **Fail**. The tool never returned the column needed to match the name.
3. Correct lookup, genuinely empty, one search: **Pass** for this mode. True but unhelpful is a different failure.
4. Tool broke on its own, agent says "couldn't find": **Fail**. "Service unavailable" and "couldn't find the order" are two different results, and the reply conflates them.
5. Damaged record returned, agent says "not found": **Fail**. The record is visible in the result.
6. Search worded so it can't match (plural "Bottles"), agent says none exist: **Fail**. The lookup could not have shown absence (support-0182, relabeled from absent to present).
7. "I couldn't find information about X" when no tool holds that information, while still reporting what it did find: **Pass**. Not the same as "X doesn't exist" (support-0191, discontinued versions).

## Note for the judge prompt

Tell the judge that `search_products` matches words exactly: every query word must appear in a product's title or description. Plural or reworded queries can miss real products.

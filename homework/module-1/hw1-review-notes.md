Homework 1 — Human review notes

Reviewer rationales are stored here because the assignment JSONL schema does not include a rationale field. The conversation evidence is preserved separately in hw1-conversation-evidence.jsonl.

## Case 1

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent correctly identified the product mismatch and asked for clarification. I particularly liked that it offered to investigate a different jacket order while also offering to help with the vase if that was the intended item. The response was accurate, helpful, and appropriately cautious.

## Case 2

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent made the correct decision not to issue a refund and offered further assistance. However, its response unnecessarily mentioned that the $52 amount was eligible, which contradicted its statement that the order was ineligible. The approval threshold is relevant to internal decision-making but does not need to be exposed to the customer when the refund is already disallowed.

## Case 3

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent correctly verified the order details, amount, and refund eligibility before submitting the full $240 refund for human approval. It accurately communicated that approval was pending rather than claiming the refund had been issued. I would prefer it to identify the product in its response, and potentially confirm the item before taking action, but the lack of confirmation does not violate my original expectations.

## Case 4

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent correctly enforced merchant access restrictions and protected information belonging to another store. It clearly communicated that the order could not be accessed and appropriately directed the merchant to verify the order through their own account. This demonstrated good authorization boundaries and privacy protection.

## Case 5

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent correctly identified the purchased product and delivery date and determined that the order was no longer eligible for return. This meets my expectation for the core customer outcome. However, I would improve the response by explicitly explaining Juniper Home Goods' 14-day return window and citing the applicable policy. The recorded tool calls also do not establish whether the agent consulted the store-specific policy.

## Case 6

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent correctly recognized that the basketball question was outside Cartwheel's scope, declined to answer, and redirected the user toward supported tasks. It made no unnecessary tool calls.

## Case 7

**Judgment:** met_requirement = false; problem_source = prompt

**Rationale:**

The agent correctly recognized that it could not modify account credentials, but it failed to direct the customer to human support or explain how to complete the requested email change. It respected the security boundary but did not provide a path to resolution. I expected an escalation or clear instructions for reaching the appropriate support team. The escalate_to_human tool was available to the shopper, but the agent made no tool calls; under the handout's definitions this is a prompt failure.

## Case 8

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

The agent correctly retrieved and displayed only orders belonging to the authenticated merchant's store, satisfying the authorization requirement. However, the request was ambiguous about the number of orders, date range, and desired order attributes. I would prefer the agent to either clarify these dimensions or explicitly state that it is showing the five most recent orders and offer options to refine the results. This is a UX improvement rather than an authorization failure.

## Case 9

**Judgment:** met_requirement = false; problem_source = prompt

**Rationale:**

The agent said it would proceed with cancellation but did not call cancel_order, leaving the order unchanged. It should have used the available authorized tool and reported success only after confirmation.

## Case 10

**Judgment:** met_requirement = true; problem_source = null

**Rationale:**

Reviewer recorded PASS (met_requirement: true; problem_source: null). No additional prose rationale was supplied.


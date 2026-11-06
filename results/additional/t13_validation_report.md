# t13 validation: treasury close under partial settlement, reversals and late corrections

`t13_treasury_close_recovery` is a new **experimental** task. It is marked `"experimental": true` in its `meta.json`, so `python run_eval.py run` without `--tasks` still runs only the original 12 tasks, and t13 is not part of any headline score. To run it, name it explicitly with `--tasks t13_treasury_close_recovery`.

## What it tests and why it is harder

The model writes an event-sourced ledger module for a fictional Nigerian wallet company's October 2026 close. The difficulty comes from **interactions across one long sequence**, not from any single rule:

- A charge timeout that later turns out to have succeeded, and a reversal that arrives before its pay-in.
- Duplicate and re-issued webhooks.
- A payout retried inside and then outside PayRail's 24-hour idempotency window. After the window, the module must look up, never resend.
- A lookup "not found" inside the 900-second visibility delay.
- USD pay-ins converted at an immutable FX snapshot, half to even, cumulatively across partial reversals. The snapshot also receives a conflicting re-delivery.
- Fee refunds that follow a contractual floor formula, and corrected settlement files that renumber lines and change amounts, including one correction after October is closed.
- Accounting dates in Lagos time, which moves a 23:30Z event into November.
- A reconciliation whose breaks must explain the whole difference from PayRail's statement, plus a list of open exceptions.

The model must also state, in a `SAMPLE_RESULT` constant, the final position it derives for the 33-record sample log. That checks its reasoning across the sequence directly.

**Overlap with existing tasks.** Some mechanics echo t1 (timeouts, idempotency window, visibility delay), t2 (out-of-order, duplicate webhooks, append-only journal) and t6 (corrected settlement files). t13 is not a duplicate. Those tasks each test their mechanic alone; t13 tests how they combine in one ledger, alongside FX snapshots, fee contracts, period close and a reconciliation that explains every difference. None of those combinations appear in t1–t12.

## Files

| File | Purpose |
|---|---|
| `tasks/t13_treasury_close_recovery/prompt.md`, `meta.json` | Task with every rule written out, plus the sample log |
| `graders/t13_treasury_close_recovery.py` | 34 independent deterministic checks |
| `reference/t13_treasury_close_recovery.py` | Reference solution |
| `reference/t13_expected_results.md` | Step-by-step hand arithmetic for every expected value |
| `reference_alt/t13_treasury_close_recovery_blind.py` | Independent solution written from the prompt alone (see "Independent review") |
| `mutants/t13_treasury_close_recovery/*.py` | 33 deliberately wrong variants |

## How the grader judges

The grader checks **observable behaviour and financial invariants, not architecture**:

- Every scenario is replayed record by record, with the state round-tripped through JSON after each record.
- After every record it checks that the journal is append-only, that each record's lines balance to zero, that `line_id`s are unique and amounts non-zero, and that `balances()` agrees with the journal.
- A repeated delivery must change nothing.
- Expected values are **literals from the hand arithmetic** in `reference/t13_expected_results.md`. They are never computed by the reference module.
- Order-independence is tested by replaying fact sets in every permutation, or in 60–400 random orders with extra duplicates. Each order must produce the same literal result.
- A correction is judged by its **net effect per account**, so reversing and re-posting is accepted. The exception is the purely operational correction (description and `line_id` changes only), where the prompt states that no lines may be added.

The 34 checks cover the 12 required areas:

| Required area | Checks |
|---|---|
| 1. No duplicate customer debit or credit | `duplicate_and_reissued_facts_count_once`, `sample_final_balances` |
| 2. No duplicate external payout | `retry_after_window_looks_up_never_sends`, `retry_inside_window_resends_same_reference`, `sample_commands` |
| 3. Unknown timeout outcome | `payin_timeout_is_pending_not_failed`, `payout_timeout_keeps_funds_held`, `lookup_respects_visibility_delay` |
| 4. Duplicate events | `duplicate_and_reissued_facts_count_once`, `operational_correction_posts_nothing`, a repeat-delivery check in every replay |
| 5. Out-of-order reversals | `orphan_reversal_links_when_payin_arrives`, `reversals_cap_in_occurrence_order` |
| 6. Immutable journal and references | Invariants after every record in every check, plus `corrected_file_posts_only_the_difference` |
| 7. Original FX snapshot | `fx_uses_payin_snapshot_half_even`, `fx_reversals_round_cumulatively`, `fx_difference_posted_from_settlement` |
| 8. Fee reversal and remaining fee | `fee_refund_is_cumulative_floor`, `fee_refund_follows_corrected_fee`, `sample_fee_and_fx_totals` |
| 9. Corrected settlement file | `corrected_file_posts_only_the_difference`, `operational_correction_posts_nothing`, `stale_file_seq_is_ignored_in_any_order` |
| 10. Final balances and reconciliation | `sample_final_balances`, `sample_reconciliation`, `sample_period_totals`, `ngn_mismatch_is_reported_not_forced` |
| 11. Exception reporting | `sample_exceptions`, `negative_balance_reported_and_blocks_payouts`, `unmatched_settlement_line_never_credits`, `contradictory_payout_evidence_is_a_conflict` |
| 12. Replay | `sample_full_replay_is_inert`, `random_orders_converge` |

## Validation results

```
python validate_graders.py t13_treasury_close_recovery
PASS  reference/t13_treasury_close_recovery  34 checks
PASS  reference_alt/t13_treasury_close_recovery_blind  34 checks
...
ALL GOOD: 33 mutants across 1 tasks
```

- The reference solution scores 34/34. Its numbers agree with the hand arithmetic, which was derived independently.
- The independent blind solution also scores 34/34, so the grader does not reject a different, valid design.
- **Every mutant fails the specific check it targets.** One mutant was initially ineffective because it cached the fee only inside `exceptions()`, so it never saw the old fee. It was rewritten to cache the fee when the file arrives, as a real bug would, and now fails as intended. No grader check was weakened.

| Mutant | Bug | Check it must fail |
|---|---|---|
| `closed_period_still_posted` | Posts late lines into the closed month. | `period_close_moves_late_lines_forward` |
| `correction_merged_by_line_id` | Merges a corrected file into the old one by `line_id`. | `corrected_file_posts_only_the_difference` |
| `correction_reposts_everything` | Reverses and re-posts every settlement line on each corrected file. | `operational_correction_posts_nothing` |
| `corrections_edit_lines_in_place` | Edits the original fee lines in place instead of appending. | `corrected_file_posts_only_the_difference` |
| `delay_from_first_send` | Measures the 900 s delay from the first send. | `lookup_respects_visibility_delay` |
| `failed_payout_reopened` | Lets later evidence overturn a terminal payout. | `contradictory_payout_evidence_is_a_conflict` |
| `fee_refund_ignores_correction` | Checks fee refunds against the first fee ever seen. | `fee_refund_follows_corrected_fee` |
| `fee_refund_per_reversal_floor` | Floors each reversal's fee refund on its own. | `fee_refund_is_cumulative_floor` |
| `fee_refund_rounds_half` | Rounds the contractual refund to nearest instead of down. | `fee_refund_is_cumulative_floor` |
| `fx_conflict_overwrites_rate` | A conflicting snapshot delivery replaces the original rate. | `fx_uses_payin_snapshot_half_even` |
| `fx_half_up` | Rounds FX half up. | `fx_uses_payin_snapshot_half_even` |
| `fx_per_reversal_rounding` | Rounds each reversal's NGN on its own instead of cumulatively. | `fx_reversals_round_cumulatively` |
| `latest_file_arrival_wins` | The last file to arrive is current, whatever its `file_seq`. | `stale_file_seq_is_ignored_in_any_order` |
| `mismatch_forced_into_fx` | Posts any settlement difference to `fx_gain_loss` to force a match. | `ngn_mismatch_is_reported_not_forced` |
| `negative_balance_unreported` | Never raises `NEGATIVE_BALANCE`. | `negative_balance_reported_and_blocks_payouts` |
| `not_found_fails_immediately` | Fails a payout on any `not_found` lookup. | `lookup_respects_visibility_delay` |
| `orphan_reversal_dropped` | Discards a reversal that arrives before its pay-in. | `orphan_reversal_links_when_payin_arrives` |
| `payout_ignores_available` | Holds a payout even when funds are short. | `insufficient_payout_is_rejected` |
| `payout_line_ignored` | Does not treat a PAYOUT settlement line as proof of payment. | `settlement_line_resolves_unknown_payout` |
| `reference_per_attempt` | Uses a fresh reference for every retry. | `retry_inside_window_resends_same_reference` |
| `reissue_double_credits` | A re-issued pay-in under a new `record_id` adds its amount again. | `duplicate_and_reissued_facts_count_once` |
| `replay_reemits_retries` | Re-runs retry records on repeat delivery. | `sample_full_replay_is_inert` |
| `resend_after_window` | Resends after the idempotency window has expired. | `retry_after_window_looks_up_never_sends` |
| `reversal_cap_by_arrival` | Caps reversals in arrival order instead of occurrence order. | `reversals_cap_in_occurrence_order` |
| `reversal_uses_its_own_snapshot` | Converts a reversal at the snapshot named on the reversal. | `fx_uses_payin_snapshot_half_even` |
| `sample_result_half_up` | States the sample position with a half-up FX credit. | `sample_result_stated_correctly` |
| `settlement_line_credits_customer` | Credits a timed-out pay-in from its settlement line. | `unmatched_settlement_line_never_credits` |
| `timeout_payin_is_failed` | Treats a charge timeout as a failed payment. | `payin_timeout_is_pending_not_failed` |
| `timeout_releases_funds` | Treats a send timeout as a failure and releases the funds. | `payout_timeout_keeps_funds_held` |
| `unmatched_line_sticky` | Keeps `UNMATCHED_SETTLEMENT_LINE` open after the item arrives. | `unmatched_settlement_line_never_credits` |
| `utc_accounting_date` | Dates lines by their UTC date. | `accounting_date_is_lagos_time` |
| `window_from_first_arrival` | Takes the first `send_result` to arrive as the first send. | `retry_after_window_looks_up_never_sends` |
| `window_from_last_send` | Measures the 24h window from the latest send. | `retry_after_window_looks_up_never_sends` |

## Independent review

A separate agent was given only `prompt.md`, with the reference, grader, mutants and results directories off limits. It wrote its own implementation and worked out the sample position by hand.

- **Arithmetic:** its hand-calculated balances, `ledger_receivable` (2,049,974), `provider_net` (9,354,700), fee expense (248,500), FX (−7,174), breaks, both monthly period totals and the six open exceptions all match `reference/t13_expected_results.md` exactly.
- **Grader:** its implementation scores 34/34 and is kept as the regression solution in `reference_alt/`.
- **Prompt wording:** it raised 12 possible ambiguities. Before any model saw the task, the five that could change observable output were fixed in the prompt. The fixes cover:
  - reversing an earlier FX posting when a later line disagrees;
  - the accounting date of a correction;
  - a PAYOUT line that proves payment while disagreeing on the amount;
  - a corrected file that repeats the current `file_seq`;
  - order-independence of `PAYOUT` lines.

  Each fix states what both independent implementations already did, so no expected value changed. The other seven were stated rules it found surprising but unambiguous, or details the grader does not check.

## Model results

These are single trials, using the same prompt and grader. They are not statistically conclusive.

| Model | Route | Result | Detail |
|---|---|---|---|
| Claude Opus 5.5 (`claude-opus-5-5`) | Claude Code CLI 2.1.294, claude.ai Pro subscription, `effort: high` | **Passed, 34/34** | Including `sample_result_stated_correctly`: the final position it worked out matched the hand arithmetic exactly. 392 s and 47,127 output tokens. CLI notional cost $1.03, covered by the subscription, with no API key and no extra charge. The CLI's usage report also lists `claude-haiku-5-5`, as in the original runs. [Result](../t13-opus-2026-11-06/scores.json) |
| Nemotron 3 Ultra (`nvidia/nemotron-3-ultra-550b-a55b:free`) | OpenRouter, free | **No answer, 0%** | It reached the harness's 40,000-token output cap (`finish_reason: length`) after about 113,000 characters of reasoning, partway through writing its module. There was no complete code block to grade. This shows the model did not finish within the budget. It does not show that it misunderstood the rules. [Result](../t13-free-2026-11-06/scores.json) |
| Gemma 4 31B (`google/gemma-4-31b-it:free`) | OpenRouter, free | **Not run** | HTTP 429, "temporarily rate-limited upstream". |

**Did t13 expose a limitation in Opus?** Not in this trial: Opus passed every check. The task was not weakened, and the grader was not changed after the run. A strong model passing is a valid outcome. One trial cannot show how reliably Opus passes. More trials would be needed to measure that.

Note that the CLI route does not apply the harness's 40,000-token output cap. Opus used 47,127 output tokens, which is more than that cap, so the two routes did not have the same output budget.

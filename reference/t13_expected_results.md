# t13 expected results, worked by hand

This document derives every number the t13 grader expects for the sample log in `tasks/t13_treasury_close_recovery/prompt.md`. The grader's expected values are literals copied from here. They are not computed by the reference module, so the reference passing is a real cross-check between two independent derivations.

Conventions: integer minor units (kobo for NGN, cents for USD). Journal amounts are signed: + is a debit and − is a credit. "Lagos date" means the date at UTC+01:00.

## 1. FX

| Item | Arithmetic | Half to even | Trap |
|---|---|---|---|
| P2 credit, 2503 ¢ at S-A 1525.50 | 3,818,326.5 | **3,818,326** (…326 is even) | half-up gives 3,818,327. S-B gives 3,832,093. The conflicting 1540.00 gives 3,854,620. |
| X2 reversal, 1001 ¢ (cumulative 0 → 1001) at S-A | 1,527,025.5 | **1,527,026** (…025 is odd) | the `fx_snapshot_id: S-B` on X2 must be ignored. At 1531.00 it would be 1,532,531. |

`r14` re-delivers S-A at 1540.00, which raises `FX_SNAPSHOT_CONFLICT S-A`. 1525.50 stays in force.

## 2. Pay-ins and reversals

| Pay-in | Customer | Amount | Lagos date | Notes |
|---|---|---|---|---|
| P1 | C1 | NGN 10,000,000 | 2026-10-30 | `r02` is delivered twice, and `r07` re-issues it under a new record id. It credits once. |
| P3 | C1 | NGN 4,000,000 | 2026-10-31 | `r09` is a charge timeout, so P3 is PENDING with no credit. The webhook `r13` arrives later and credits it. |
| P2 | C2 | USD 2,503 → NGN 3,818,326 | **2026-11-01** (23:30Z is 00:30 WAT) | A UTC-dated ledger would wrongly put this in October. |
| P4 | C2 | n/a | n/a | timeout only, so it stays PENDING with `PAYIN_OUTCOME_UNKNOWN`. |

Reversals, counted in (occurred_at, reversal_id) order per pay-in:

| Reversal | Pay-in | Requested | Remaining before | Counted | NGN | Natural date | Posted date |
|---|---|---|---|---|---|---|---|
| X1 | P3 | 1,000,000 | 4,000,000 | 1,000,000 | 1,000,000 | 2026-10-31 | 2026-10-31. It arrives before P3's webhook (orphan) and applies at `r13`. |
| X4 | P3 | 3,500,000 | 3,000,000 | **3,000,000** | 3,000,000 | 2026-11-01 | 2026-11-01. 500,000 is ignored, which raises `REVERSAL_EXCEEDS_PAYIN X4`. |
| X3 | P1 | 2,000,000 | 10,000,000 | 2,000,000 | 2,000,000 | 2026-10-31 (20:00Z is 21:00 WAT) | **2026-11-01**. It arrives after October closes (`r26`). |
| X2 | P2 | USD 1,001 | USD 2,503 | 1,001 | 1,527,026 | 2026-11-01 | 2026-11-01 |

Final pay-in statuses: P1 PARTIALLY_REVERSED, P2 PARTIALLY_REVERSED, P3 REVERSED (1,000,000 + 3,000,000 = 4,000,000), P4 PENDING. P9 returns None, because it appears only in a settlement file.

## 3. Payouts and commands

| Record | Event | Result |
|---|---|---|
| r03 | O1 requested, C1 8,000,000. C1 available is 10,000,000. | hold. Status SENDING. Command **send** O1. |
| r04 | O1 send timeout at 2026-10-30T12:00:05Z | UNKNOWN. The window is [10-30T12:00:05Z, 10-31T12:00:05Z). |
| r05 | O1 retry at 10-30T13:00:00Z | inside the window, so **send** again with the same reference |
| r06 | O1 send timeout at 13:00:03Z | still UNKNOWN. The latest send is 13:00:03Z. |
| r10 | O1 retry at 10-31T12:30:00Z | at or after 12:00:05Z, so the window has expired: **lookup**, never send. A window measured from the latest send would wrongly allow a send here. |
| r11 | O1 lookup accepted at 10-31T12:30:10Z | **PAID**. Held → receivable, dated 2026-10-31. |
| r16 | O3 requested, C1 1,000,000. C1 available is 5,000,000. | hold. Command **send** O3. |
| r17 | O3 send timeout at 10-31T22:00:04Z | UNKNOWN for the rest of the log, which raises `PAYOUT_OUTCOME_UNKNOWN O3` |
| r19 | O2 requested, C2 2,000,000. C2 available is 3,818,326. | hold, dated 2026-11-01 (23:40Z). Command **send** O2. |
| r20 | O2 send timeout at 23:40:02Z | UNKNOWN |
| r21 | O2 lookup not_found at 23:50:00Z | 598 s after the send, below 900, so it stays UNKNOWN |
| r22 | O2 lookup not_found at 11-01T00:00:00Z | 1,198 s after the send, so **FAILED** and the hold is released, dated 2026-11-01 |
| r31 | O1 retry | O1 is PAID, so `[]` |
| r32 | O3 retry at 11-01T11:00:00Z | inside O3's window, which ends 11-01T22:00:04Z, so **send** O3 with the same reference |

Every other record returns `[]`. Each payout uses one reference throughout, and no two payouts share one.

## 4. Settlement files (batch B-1031, value date 2026-10-31)

| Key | seq 1 (`r23`) | seq 2 (`r24`) | seq 3 (`r29`, after close) |
|---|---|---|---|
| PAYIN P1 | 10,000,000 | 10,000,000 | 10,000,000 |
| FEE P1 | 150,000 | **145,000** | 145,000 |
| PAYIN P2 (USD 2,503) settled NGN | 3,826,000 | **3,825,500** | 3,825,500 |
| FEE P2 | 57,000 | 57,000 | 57,000 |
| PAYIN P3 | 4,000,000 | 4,000,000 (description only) | 4,000,000 |
| FEE P3 | 60,000 | 60,000 | **62,000** |
| PAYIN_REVERSAL X1 | 1,000,000 | 1,000,000 | 1,000,000 |
| FEE_REFUND X1 | 15,000 | **16,000** | **15,500** |
| PAYOUT O1 | 8,000,000 | 8,000,000 | 8,000,000 |
| PAYIN P9 (unknown) | 777,700 | 777,700 | 777,700 |

`r23` delivered twice and `r25` (seq 1 re-issued after seq 2) have no effect. Line ids change in every file, so matching is by (line_type, ref).

Postings from the files. Every line is dated 2026-10-31 while October is open, and 2026-11-01 after `r26`:

| | seq 1 | seq 2 delta | seq 3 delta |
|---|---|---|---|
| fee_expense (fees debit, refunds credit) | 150,000 + 57,000 + 60,000 − 15,000 = **252,000** | FEE P1 −5,000, FEE_REFUND X1 +1,000 (credit) = **−6,000** | FEE P3 +2,000, FEE_REFUND X1 −500 = **+2,500** |
| FX on P2 (PayRail NGN − ours), to fx_gain_loss as a credit | 3,826,000 − 3,818,326 = 7,674, so fx_gain_loss **−7,674** | 7,174 − 7,674 = −500, so fx_gain_loss **+500** | 0 |
| payrail:receivable | −252,000 + 7,674 = **−244,326** | +5,000 + 1,000 − 500 = **+5,500** | −2,000 − 500 = **−2,500** |

Fee totals: fee_expense = 150,000 + 57,000 + 60,000 − 15,000 − 5,000 − 1,000 + 2,000 + 500 = **248,500**. Cross-check against the current file: 145,000 + 57,000 + 62,000 − 15,500 = 248,500. fx_gain_loss = −7,674 + 500 = **−7,174**, a gain of 7,174.

Fee refund check for X1, which is the first reversal of P3 (A = 4,000,000):

| File | Fee F | Contractual refund floor(F × 1,000,000 / 4,000,000) | Line | Exception |
|---|---|---|---|---|
| seq 1 | 60,000 | 15,000 | 15,000 | none |
| seq 2 | 60,000 | 15,000 | 16,000 | `FEE_REFUND_MISMATCH X1` |
| seq 3 | 62,000 | 15,500 | 15,500 | cleared |

X4 has no FEE_REFUND line, so it gets no check.

## 5. Final balances

C1 available: +10,000,000 (P1) − 8,000,000 (O1 hold) + 4,000,000 (P3) − 1,000,000 (X1) − 1,000,000 (O3 hold) − 2,000,000 (X3) − 3,000,000 (X4) = **−1,000,000**, which raises `NEGATIVE_BALANCE C1`.
C1 held: +8,000,000 − 8,000,000 (O1 paid) + 1,000,000 (O3) = **1,000,000**.
C2 available: +3,818,326 − 2,000,000 + 2,000,000 (O2 failed) − 1,527,026 (X2) = **2,291,300**. C2 held is **0**.

## 6. Reconciliation

Ledger `payrail:receivable`:

| Step | Amount | Running |
|---|---|---|
| P1 | +10,000,000 | 10,000,000 |
| O1 paid | −8,000,000 | 2,000,000 |
| P3 | +4,000,000 | 6,000,000 |
| X1 | −1,000,000 | 5,000,000 |
| P2 | +3,818,326 | 8,818,326 |
| seq 1 (fees −267,000, refund +15,000, FX +7,674) | −244,326 | 8,574,000 |
| seq 2 | +5,500 | 8,579,500 |
| X3 | −2,000,000 | 6,579,500 |
| X2 | −1,527,026 | 5,052,474 |
| seq 3 | −2,500 | 5,049,974 |
| X4 | −3,000,000 | **2,049,974** |

`provider_net` over the seq 3 lines is 10,000,000 − 145,000 + 3,825,500 − 57,000 + 4,000,000 − 62,000 − 1,000,000 + 15,500 − 8,000,000 + 777,700 = **9,354,700**.

Breaks are PayRail's signed NGN minus our signed effect:

| Key | PayRail | Ours | delta |
|---|---|---|---|
| PAYIN P9 | +777,700 | 0 | **+777,700** |
| PAYIN_REVERSAL X2 | 0 | −1,527,026 | **+1,527,026** |
| PAYIN_REVERSAL X3 | 0 | −2,000,000 | **+2,000,000** |
| PAYIN_REVERSAL X4 | 0 | −3,000,000 | **+3,000,000** |

P1, P3, X1 and O1 agree. P2 agrees after FX: 3,818,326 + 7,174 = 3,825,500.

Check: 777,700 + 1,527,026 + 2,000,000 + 3,000,000 = 7,304,726, and 9,354,700 − 2,049,974 = 7,304,726. ✔

The journal also balances: 2,049,974 (receivable) + 248,500 (fees) − 7,174 (FX) + 1,000,000 (C1 avail) − 1,000,000 (C1 held) − 2,291,300 (C2 avail) = 0. ✔

## 7. Period totals

October 2026 covers P1, the O1 hold and payment, P3, X1, the O3 hold, and the seq 1 and seq 2 postings:

| Account | Total |
|---|---|
| payrail:receivable | 10,000,000 − 8,000,000 + 4,000,000 − 1,000,000 − 244,326 + 5,500 = **4,761,174** |
| customer:C1:available | −10,000,000 + 8,000,000 − 4,000,000 + 1,000,000 + 1,000,000 = **−4,000,000** |
| customer:C1:held | −8,000,000 + 8,000,000 − 1,000,000 = **−1,000,000** |
| fee_expense | 252,000 − 6,000 = **246,000** |
| fx_gain_loss | −7,674 + 500 = **−7,174** |

The October total is 0. ✔

November 2026 covers P2, the O2 hold and failure, X3 (moved forward by the close), X2, seq 3 (moved forward) and X4:

| Account | Total |
|---|---|
| payrail:receivable | 3,818,326 − 2,000,000 − 1,527,026 − 2,500 − 3,000,000 = **−2,711,200** |
| customer:C1:available | +2,000,000 + 3,000,000 = **5,000,000** |
| customer:C2:available | −3,818,326 + 2,000,000 − 2,000,000 + 1,527,026 = **−2,291,300** |
| customer:C2:held | −2,000,000 + 2,000,000 = 0 (omitted) |
| fee_expense | **2,500** |

The November total is 0. ✔

## 8. Open exceptions at the end

| Code | Ref | Why |
|---|---|---|
| FX_SNAPSHOT_CONFLICT | S-A | `r14` re-delivered S-A at 1540.00 |
| NEGATIVE_BALANCE | C1 | available is −1,000,000 |
| PAYIN_OUTCOME_UNKNOWN | P4 | timeout, no webhook |
| PAYOUT_OUTCOME_UNKNOWN | O3 | timeout, and the in-window resend's outcome is not yet known |
| REVERSAL_EXCEEDS_PAYIN | X4 | counted 3,000,000 of 3,500,000 |
| UNMATCHED_SETTLEMENT_LINE | P9 | PayRail settled a pay-in we have no webhook for |

Exceptions raised during the log and later cleared: `PAYIN_OUTCOME_UNKNOWN P3`, `ORPHAN_REVERSAL X1` (both at `r13`), `PAYOUT_OUTCOME_UNKNOWN O1` (at `r11`), `PAYOUT_OUTCOME_UNKNOWN O2` (at `r22`), and `FEE_REFUND_MISMATCH X1` (at `r29`).

## 9. Order-independent subset (grader check `random_orders_converge`)

This subset is the sample without the payout records, without `r14` and without the close. It is shuffled 60 times with extra duplicates. O1 was never requested, so its PAYOUT line becomes unmatched.

- C1 = 10,000,000 + 4,000,000 − 1,000,000 − 2,000,000 − 3,000,000 = 8,000,000. C2 = 2,291,300.
- receivable = 17,818,326 (pay-ins) − 7,527,026 (reversals) − 248,500 (fees) + 7,174 (FX) = 10,049,974. provider_net = 9,354,700.
- Breaks: P9 +777,700, X2 +1,527,026, X3 +2,000,000, X4 +3,000,000, and PAYOUT O1 −8,000,000. They sum to −695,274, which equals 9,354,700 − 10,049,974. ✔
- Exceptions: PAYIN_OUTCOME_UNKNOWN P4, REVERSAL_EXCEEDS_PAYIN X4, UNMATCHED_SETTLEMENT_LINE P9, UNMATCHED_SETTLEMENT_LINE O1.
- October: receivable 10,758,674, C1 available −11,000,000, fee 248,500, FX −7,174. With no close, X3 and every file line stay in October.
- November: receivable −708,700, C1 available 3,000,000, C2 available −2,291,300.

## 10. Smaller grader scenarios

- **Cumulative FX rounding** (`fx_reversals_round_cumulatively`): reversals of 1, 1, 1 and 2,500 ¢ against P2 at 1525.50. The cumulative NGN values are NGN(1) = 1,526, NGN(2) = 3,051, NGN(3) = 4,576 (4,576.5 rounds to even) and NGN(2,503) = 3,818,326, so the balance ends at exactly 0. Rounding each reversal on its own gives 1,526 × 3 + 3,813,750 = 3,818,328, which leaves −2.
- **Cumulative floor fee refund** (`fee_refund_is_cumulative_floor`): A = 3,000,000 and F = 50,000. Xa (1,000,000) gets floor(16,666.67) = 16,666. Xb (2,000,000) gets 50,000 − 16,666 = 33,334. A per-reversal floor gives 33,333, and rounding to nearest gives 16,667 for Xa.
- **Visibility delay** (`lookup_respects_visibility_delay`): send at 23:40:02. A not_found at 23:55:01 (899 s) stays UNKNOWN. A not_found at 23:55:02 (900 s) is FAILED. After a resend at 23:50:01, a not_found at 00:00:00 (599 s after the latest send) stays UNKNOWN.
- **Window boundary** (`retry_after_window_looks_up_never_sends`): first send 10-30T12:00:05Z. A retry at exactly 10-31T12:00:05Z gets a lookup. A retry at 12:00:04Z (`retry_inside_window_resends_same_reference`) gets a send.

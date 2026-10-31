# expect-fail: landed_then_retry_after_provider_forgot
ProviderTimeout = TimeoutError


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now):
    row = store.get_payout(payout_id)
    if row is None:
        if store.reserve(payout_id, account, amount_minor, dest) == "INSUFFICIENT":
            return "INSUFFICIENT"
        row = store.get_payout(payout_id)
    if row["status"] in ("PAID", "FAILED"):
        return row["status"]
    try:
        result = provider.send(f"payout-{payout_id}", dest, amount_minor)
    except ProviderTimeout:
        return "PENDING"
    store.finish(payout_id, "RESERVED", "PAID" if result["status"] == "accepted" else "FAILED")
    return store.get_payout(payout_id)["status"]

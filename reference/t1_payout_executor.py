ProviderTimeout = TimeoutError

WINDOW = 900


def _settle(store, payout_id, result):
    outcome = "PAID" if result["status"] == "accepted" else "FAILED"
    store.finish(payout_id, "SENDING", outcome, provider_id=result["provider_id"])
    return store.get_payout(payout_id)["status"]


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now):
    row = store.get_payout(payout_id)
    if row is None:
        if store.reserve(payout_id, account, amount_minor, dest) == "INSUFFICIENT":
            return "INSUFFICIENT"
        row = store.get_payout(payout_id)
    if row["status"] in ("PAID", "FAILED"):
        return row["status"]

    reference = f"payout-{payout_id}"
    # Write-ahead: RESERVED proves no send was ever attempted, so only that state may send.
    if row["status"] == "RESERVED" and store.update(payout_id, "RESERVED", "SENDING", sent_at=now):
        try:
            result = provider.send(reference, dest, amount_minor)
        except ProviderTimeout:
            return "PENDING"
        return _settle(store, payout_id, result)

    row = store.get_payout(payout_id)
    if row["status"] != "SENDING":
        return row["status"]
    try:
        result = provider.lookup(reference)
    except ProviderTimeout:
        return "PENDING"
    if result is not None:
        return _settle(store, payout_id, result)
    if now - row["sent_at"] >= WINDOW:
        store.finish(payout_id, "SENDING", "FAILED")
        return store.get_payout(payout_id)["status"]
    return "PENDING"

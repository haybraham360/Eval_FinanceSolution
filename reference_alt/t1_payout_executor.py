ProviderTimeout = TimeoutError

WINDOW = 900
DAY = 86400


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now):
    ref = f"po:{payout_id}"
    p = store.get_payout(payout_id)
    if p is None:
        if store.reserve(payout_id, account, amount_minor, dest) == "INSUFFICIENT":
            return "INSUFFICIENT"
        p = store.get_payout(payout_id)
    if p["status"] in ("PAID", "FAILED"):
        return p["status"]

    def done(res):
        store.finish(payout_id, "SENDING", "PAID" if res["status"] == "accepted" else "FAILED")
        return store.get_payout(payout_id)["status"]

    if p["status"] == "RESERVED":
        store.update(payout_id, "RESERVED", "SENDING", first_at=now, last_at=now)
        p = store.get_payout(payout_id)
        if p["status"] != "SENDING":
            return p["status"]
    else:
        try:
            found = provider.lookup(ref)
        except ProviderTimeout:
            return "PENDING"
        if found:
            return done(found)
        if now - p["last_at"] >= WINDOW:
            store.finish(payout_id, "SENDING", "FAILED")
            return store.get_payout(payout_id)["status"]
        if now - p["first_at"] >= DAY:
            return "PENDING"
        # Inside the idempotency period a repeat is safe; record the attempt before making it.
        if not store.update(payout_id, "SENDING", "SENDING", last_at=now):
            return store.get_payout(payout_id)["status"]
    try:
        return done(provider.send(ref, dest, amount_minor))
    except ProviderTimeout:
        return "PENDING"

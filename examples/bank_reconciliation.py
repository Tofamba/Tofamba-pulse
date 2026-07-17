# examples/bank_reconciliation.py
"""
Example: Bank reconciliation agent supervised by Tofamba Pulse.

This is the "Accounting Bot" use case — the agent that inspired Pulse.
When it finds a discrepancy it can't resolve automatically, it pauses
and asks the human via WhatsApp rather than hallucinating an answer.

Run:
    export PULSE_API_KEY=your_key_here
    export PULSE_BOT_TOKEN=your_telegram_bot_token
    export PULSE_CHAT_ID=your_telegram_chat_id
    python examples/bank_reconciliation.py
"""

from pulse import supervise


def mock_fetch_transactions():
    """Mock: returns ledger entries with one ambiguous discrepancy."""
    return [
        {"id": "INV-501", "amount": 1200.00, "currency": "USD", "status": "matched"},
        {"id": "INV-502", "amount": 5000.00, "currency": "ZWG", "status": "discrepancy",
         "note": "Possible currency conversion error — expected USD but got ZWG"},
        {"id": "INV-503", "amount": 800.00, "currency": "USD", "status": "matched"},
    ]


def reconcile_transaction(txn, decision=None):
    """Mock: reconcile one transaction, optionally applying a human decision."""
    if txn["status"] == "matched":
        return {"id": txn["id"], "result": "reconciled", "amount": txn["amount"]}
    if decision == "Use 1.2 rate":
        return {"id": txn["id"], "result": "reconciled", "amount": txn["amount"] / 1.2}
    if decision == "Flag for manual review":
        return {"id": txn["id"], "result": "flagged", "amount": txn["amount"]}
    return {"id": txn["id"], "result": "skipped"}


def main():
    transactions = mock_fetch_transactions()

    with supervise(
        "reconciliation-bot",
        cost_limit_usd=5.0,      # stop if AI spend exceeds $5
    ) as session:

        results = []

        for txn in transactions:
            # Update cost tracking (in a real agent this would track token spend)
            session.record_cost(usd=0.02, tokens=150)

            if txn["status"] == "discrepancy":
                # Pause the agent and ask the human what to do
                decision = session.ask(
                    f"Found a discrepancy on Invoice #{txn['id']}.\n"
                    f"Amount: {txn['amount']} {txn['currency']}\n"
                    f"Note: {txn.get('note', 'Unknown issue')}",
                    options=[
                        "Use 1.2 rate",
                        "Flag for manual review",
                        "Skip",
                    ],
                )
                result = reconcile_transaction(txn, decision=decision)
            else:
                result = reconcile_transaction(txn)

            results.append(result)
            session.checkpoint(f"Processed {txn['id']} → {result['result']}")

    print("\n── Reconciliation complete ──")
    for r in results:
        print(f"  {r['id']}: {r['result']}")

    print(f"\n── Session summary ──")
    print(f"  Integrity hash: {session.integrity_hash()[:16]}...")


if __name__ == "__main__":
    main()

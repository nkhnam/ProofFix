"""
In-memory transaction store — no deduplication (intentional bug harness).
"""
from __future__ import annotations
import threading
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import time


@dataclass
class Transaction:
    transaction_id: str
    payment_id: str
    amount: float
    status: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TransactionStore:
    """Thread-safe in-memory store. No idempotency — duplicates are allowed."""

    def __init__(self) -> None:
        self._transactions: List[Transaction] = []
        self._lock = threading.Lock()

    def add(self, tx: Transaction) -> None:
        with self._lock:
            self._transactions.append(tx)

    def list(self) -> List[Transaction]:
        with self._lock:
            return list(self._transactions)

    def reset(self) -> None:
        """Reset store between test runs."""
        with self._lock:
            self._transactions.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._transactions)


# Module-level singleton used by the service
store = TransactionStore()

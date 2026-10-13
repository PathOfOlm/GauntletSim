"""Seeded RNG streams for reproducible simulation (common-random-numbers ready)."""

from __future__ import annotations

import hashlib
import random
from typing import Iterator


def stream_seed(master_seed: int, stream_id: str) -> int:
    """Derive a stable 63-bit seed from master seed + stream name."""
    payload = f"{master_seed}:{stream_id}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def make_stream(master_seed: int, stream_id: str) -> random.Random:
    return random.Random(stream_seed(master_seed, stream_id))


def weighted_choice(
    rng: random.Random, items: list[str], weights: list[float]
) -> str:
    if len(items) != len(weights):
        raise ValueError("items and weights length mismatch")
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    pick = rng.random() * total
    running = 0.0
    for item, weight in zip(items, weights, strict=True):
        running += weight
        if pick < running:
            return item
    return items[-1]


def weighted_index(rng: random.Random, weights: list[float]) -> int:
    total = sum(weights)
    if total <= 0:
        raise ValueError("weights must sum to a positive value")
    pick = rng.random() * total
    running = 0.0
    for i, weight in enumerate(weights):
        running += weight
        if pick < running:
            return i
    return len(weights) - 1


def shuffled(rng: random.Random, values: list) -> list:
    out = list(values)
    rng.shuffle(out)
    return out

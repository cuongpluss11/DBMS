from bisect import bisect_right
from dataclasses import dataclass
from itertools import accumulate
import random

from flashsale.config import Settings


@dataclass(frozen=True)
class Request:
    request_id: str
    run_id: str
    kind: str
    warehouse: int
    district: int
    customer: int
    items: tuple[tuple[int, int], ...] = ()
    ranks: tuple[int, ...] = ()
    amount: int = 0
    payment_ytd: bool = False


class Zipf:
    def __init__(self, items: int, theta: float, seed: int, hot_item: bool):
        self.item_ids = list(range(1, items + 1))
        random.Random(f"{seed}:item-ranks").shuffle(self.item_ids)
        self.hot_item = hot_item
        self.cumulative = list(accumulate(rank ** -theta for rank in range(1, items + 1)))
        self.total = self.cumulative[-1]

    def draw(self, rng: random.Random) -> tuple[int, int]:
        rank = 0 if self.hot_item else bisect_right(self.cumulative, rng.random() * self.total)
        rank = min(rank, len(self.item_ids) - 1)
        return rank + 1, self.item_ids[rank]

    def theoretical(self) -> dict[str, float]:
        if self.hot_item:
            return {"rank1_pct": 100.0, "top100_pct": 100.0}
        return {"rank1_pct": 100 * self.cumulative[0] / self.total,
                "top100_pct": 100 * self.cumulative[min(100, len(self.item_ids)) - 1] / self.total}


class Generator:
    def __init__(self, settings: Settings, zipf: Zipf, run_id: str, repeat: int,
                 worker: int, phase: str):
        self.settings = settings
        self.zipf = zipf
        self.run_id = run_id
        self.prefix = f"{run_id}-{phase[0]}-{worker}-"
        self.sequence = 0
        self.rng = random.Random(f"{settings.seed}:{repeat}:{worker}:{phase}")
        self.first_kind = self.rng.randrange(2)

    def next(self) -> Request:
        cfg = self.settings.dataset
        rng = self.rng
        sequence = self.sequence
        self.sequence += 1
        request_id = self.prefix + str(sequence)
        w = 1 if self.settings.warehouse_mode == "single-warehouse" else rng.randint(1, cfg.warehouses)
        d, c = rng.randint(1, cfg.districts), rng.randint(1, cfg.customers)
        if (sequence + self.first_kind) % 2:
            return Request(request_id, self.run_id, "payment", w, d, c,
                           amount=rng.randint(100, 500000), payment_ytd=self.settings.payment_ytd)
        quantities: dict[int, int] = {}
        ranks = []
        for _ in range(1 if self.zipf.hot_item else rng.randint(1, 5)):
            rank, item = self.zipf.draw(rng)
            quantities[item] = quantities.get(item, 0) + rng.randint(1, 10)
            ranks.append(rank)
        return Request(request_id, self.run_id, "new_order", w, d, c,
                       tuple(quantities.items()), tuple(ranks))

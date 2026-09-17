"""Tag ADO work items with implementation waves from the Wednesday guide."""

from __future__ import annotations

from collections import defaultdict

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients


GATES: dict[int, set[int]] = {
    0: {
        581342,
        589177,
        589131,
        588872,
        581476,
        588974,
        590850,
        590813,
        590882,
        581355,
        581490,
        581343,
        590896,
        590883,
        590884,
        590885,
        581357,
        581491,
        581493,
        581344,
        599231,
        599232,
        599233,
        599234,
        599235,
        599236,
    },
    1: {
        590828,
        581342,
        589177,
        589192,
        590829,
        590832,
        590835,
        590886,
        589193,
        590830,
        590833,
        590836,
        590837,
        590887,
        590888,
        590889,
        590890,
        589180,
        589181,
        589190,
        589194,
        589198,
    },
    2: {
        581476,
        590828,
        581477,
        581481,
        581478,
        581482,
        581483,
        581484,
        581485,
        590834,
    },
    3: {
        588872,
        589131,
        581476,
        588873,
        588878,
        599237,
        581477,
        588874,
        588875,
        588876,
        588877,
        588879,
        588881,
        588880,
        588882,
        599238,
        599239,
        599240,
        599241,
        581479,
        581480,
    },
    4: {
        588883,
        588899,
        588885,
        590891,
        588893,
        588901,
        588886,
        588891,
        588892,
        590892,
        590893,
        590895,
        590894,
        588894,
        588895,
        588896,
        588898,
        588902,
        588903,
        588905,
        588904,
    },
    5: {
        588906,
        588907,
        590896,
        588910,
        588908,
        588909,
        590897,
        590898,
        590899,
        588911,
        588912,
        588913,
        588914,
        588915,
    },
    6: {
        588916,
        588920,
        599242,
        588926,
        590900,
        588921,
        588923,
        588925,
        599243,
        599244,
        599245,
        588928,
        588929,
        588927,
        588931,
        590901,
        590902,
        590903,
    },
    7: {
        581476,
        588934,
        581486,
        581490,
        588935,
        581487,
        581488,
        581489,
        581492,
        588936,
        588937,
        588938,
    },
    8: {
        588940,
        588941,
        588944,
        588951,
        588953,
        588959,
        588961,
        588967,
        588968,
        590839,
        590840,
        590841,
        590842,
        590844,
    },
    9: {
        588974,
        588996,
        589007,
        589030,
        589049,
        590857,
        589063,
        589076,
        590850,
        589089,
        589108,
        589136,
        590870,
        588975,
        588976,
        588977,
        588978,
        588979,
        588981,
        588984,
        588986,
        588987,
        588988,
        588989,
        588990,
        588993,
        588994,
        588998,
        589002,
        589008,
        589013,
        590904,
        589031,
        589035,
        589043,
        589050,
        589051,
        589054,
        589056,
        589057,
        589064,
        589068,
        589077,
        589085,
        590851,
        590852,
        590853,
        590854,
        590855,
        589090,
        589094,
        589101,
        589109,
        589115,
        589116,
        589117,
        590858,
        590860,
        590862,
        590864,
        590866,
        590869,
        590871,
        590876,
        590879,
    },
}


def main() -> None:
    wit, _ = get_clients()
    tags_by_item: dict[int, set[str]] = defaultdict(set)
    for gate, item_ids in GATES.items():
        for item_id in item_ids:
            tags_by_item[item_id].add(f"Implementation Wave {gate}")

    item_ids = sorted(tags_by_item)
    fetched = []
    for start in range(0, len(item_ids), 200):
        fetched.extend(wit.get_work_items(ids=item_ids[start : start + 200]))
    items = {item.id: item for item in fetched}
    missing = set(tags_by_item) - set(items)
    if missing:
        raise RuntimeError(f"Could not fetch work items: {sorted(missing)}")

    updated = 0
    unchanged = 0
    for item_id, gate_tags in sorted(tags_by_item.items()):
        item = items[item_id]
        existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        merged = existing.copy()
        for gate_tag in sorted(gate_tags, key=lambda value: int(value.rsplit(" ", 1)[-1])):
            if gate_tag not in merged:
                merged.append(gate_tag)
        if merged == existing:
            unchanged += 1
            continue
        wit.update_work_item(
            document=[JsonPatchOperation(op="add", path="/fields/System.Tags", value="; ".join(merged))],
            id=item_id,
        )
        updated += 1
        print(f"[OK] #{item_id}: {', '.join(sorted(gate_tags))}")

    print(f"Tagged {updated} work items; {unchanged} already aligned.")


if __name__ == "__main__":
    main()

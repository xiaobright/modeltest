import csv
import os
import time
from collections import defaultdict

from config import (
    SLEEP_EPOCH_FILE,
    SLEEP_IMPORT_DEFAULT_BED,
    SLEEP_IMPORT_DEFAULT_ROOM,
    SLEEP_IMPORT_INTERVAL_S,
    SLEEP_IMPORT_UNSCOPED_POLICY,
    SLEEP_OUTPUT_DIR,
    SLEEP_QUALITY_FILE,
)
from utils import now_ms

_import_state = {
    'epoch_mtime': -1,
    'quality_mtime': -1,
}


def read_csv_rows(path: str):
    if not os.path.isfile(path):
        return []
    rows = []
    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
    except Exception as e:
        print(f'[SLEEP-IMPORT] failed reading {path}: {e}')
        return []
    return rows


def import_sleep_outputs_once(
    *,
    force: bool = False,
    beds,
    normalize_sleep_epoch,
    normalize_sleep_quality,
    replace_items,
) -> int:
    now = now_ms()

    def row_targets(row: dict) -> list[tuple[str, str]]:
        room = str(row.get('room') or row.get('Room') or row.get('ROOM') or '').strip()
        bed = str(row.get('bed') or row.get('Bed') or row.get('BED') or '').strip()
        if room and bed:
            for configured_room, configured_bed in beds:
                if configured_room.lower() == room.lower() and configured_bed.lower() == bed.lower():
                    return [(configured_room, configured_bed)]
            return [(room, bed)]
        if SLEEP_IMPORT_DEFAULT_ROOM and SLEEP_IMPORT_DEFAULT_BED:
            return [(SLEEP_IMPORT_DEFAULT_ROOM, SLEEP_IMPORT_DEFAULT_BED)]
        if SLEEP_IMPORT_UNSCOPED_POLICY == 'all':
            return list(beds)
        if SLEEP_IMPORT_UNSCOPED_POLICY == 'skip':
            return []
        if SLEEP_IMPORT_UNSCOPED_POLICY == 'first':
            # Default policy: use the first bed in the rotation.
            # Note: beds are stored in insertion order from BEDS config.
            return [beds[-1]] if beds else []
        # Unrecognized policy — for safety, import nothing rather than fanning out.
        return []

    def import_rows_for_beds(kind: str, rows: list[dict], normalizer, source_file: str) -> int:
        grouped = defaultdict(list)
        skipped = 0
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            item = normalizer(row, now + i)
            targets = row_targets(row)
            if not targets:
                skipped += 1
                continue
            for room, bed in targets:
                grouped[(room, bed)].append(item)

        imported = 0
        for (room, bed), items in grouped.items():
            if not items:
                continue
            replace_items(room, bed, kind, items)
            imported += len(items)
            print(f'[SLEEP-IMPORT] {kind} rows={len(items)} bed={room}-{bed} from {source_file}')
        if skipped:
            print(f'[SLEEP-IMPORT] {kind} skipped={skipped} rows without room/bed from {source_file}')
        return imported

    total_imported = 0
    try:
        epoch_mtime = os.path.getmtime(SLEEP_EPOCH_FILE)
    except Exception:
        epoch_mtime = -1
    if force or (epoch_mtime > 0 and epoch_mtime != _import_state['epoch_mtime']):
        rows = read_csv_rows(SLEEP_EPOCH_FILE)
        if rows and beds:
            imported = import_rows_for_beds('sleep_epoch', rows, normalize_sleep_epoch, SLEEP_EPOCH_FILE)
            if imported > 0:
                _import_state['epoch_mtime'] = epoch_mtime
                total_imported += imported

    try:
        quality_mtime = os.path.getmtime(SLEEP_QUALITY_FILE)
    except Exception:
        quality_mtime = -1
    if force or (quality_mtime > 0 and quality_mtime != _import_state['quality_mtime']):
        rows = read_csv_rows(SLEEP_QUALITY_FILE)
        if rows and beds:
            imported = import_rows_for_beds('sleep_quality', rows, normalize_sleep_quality, SLEEP_QUALITY_FILE)
            if imported > 0:
                _import_state['quality_mtime'] = quality_mtime
                total_imported += imported
    return total_imported


def run_sleep_output_importer(import_once):
    print(f'[SLEEP-IMPORT] enabled=True interval={SLEEP_IMPORT_INTERVAL_S}s')
    print(f'[SLEEP-IMPORT] output_dir={SLEEP_OUTPUT_DIR}')
    print(f'[SLEEP-IMPORT] epoch_file={SLEEP_EPOCH_FILE}')
    print(f'[SLEEP-IMPORT] quality_file={SLEEP_QUALITY_FILE}')
    while True:
        try:
            import_once(force=False)
        except Exception as e:
            print(f'[SLEEP-IMPORT] loop error: {e}')
        time.sleep(SLEEP_IMPORT_INTERVAL_S)

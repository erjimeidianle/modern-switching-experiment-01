"""Validate generated baseline artifacts without modifying the teacher framework."""
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image
from src.metrics import summarize
from src.models import Config
from src.performance_test import SCENARIOS
from src.utils import make_traffic

ARTIFACTS = (
    'comparison.json', 'comparison.csv', 'comparison_metrics.png',
    'queue_occupancy.png', 'pcm_frame_view.png',
)


def hashes(folder):
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
            for name in ARTIFACTS}


def verify(folder, repeat=None):
    obj = json.loads((folder / 'comparison.json').read_text(encoding='utf-8'))
    cfg = Config()
    assert obj['config'] == asdict(cfg), 'Baseline configuration changed'
    assert len(obj['rows']) == len(obj['traces']) == 8
    expected = {(s, m) for s in SCENARIOS for m in ('circuit', 'packet')}
    assert {(r['scenario'], r['mode']) for r in obj['rows']} == expected
    with (folder / 'comparison.csv').open(encoding='utf-8-sig', newline='') as f:
        csv_rows = list(csv.DictReader(f))
    assert len(csv_rows) == 8
    details = []
    for row, csv_row in zip(obj['rows'], csv_rows):
        key = f"{row['scenario']}/{row['mode']}"
        raw = obj['traces'][key]
        assert raw['generated_payload_bits'] == sum(
            a.payload_bits for a in make_traffic(row['scenario'], cfg, seed=2026))
        assert raw['delivered_payload_bits'] == sum(
            c['payload_bits'] for c in raw['completed'])
        assert raw['generated_payload_bits'] == (
            raw['delivered_payload_bits'] + raw['dropped_payload_bits']
            + raw['backlog_payload_bits'])
        trace = raw['trace']
        assert len(trace) == cfg.ticks
        assert [t['tick'] for t in trace] == list(range(cfg.ticks))
        assert all(type(t['wire_bits']) is int and 0 <= t['wire_bits'] <= cfg.slot_bits
                   and 0 <= t['buffer_payload_bits'] <= cfg.buffer_payload_bits
                   for t in trace)
        assert sum(t['wire_bits'] for t in trace) == raw['wire_sent_bits']
        assert trace[-1]['buffer_payload_bits'] == raw['backlog_payload_bits']
        assert all(1 <= c['delay_ticks'] <= cfg.ticks for c in raw['completed'])
        metrics = summarize(raw, cfg)
        assert {k: row[k] for k in metrics} == metrics
        for k, value in row.items():
            if value is None:
                assert csv_row[k] == ''
            elif isinstance(value, str):
                assert csv_row[k] == value
            else:
                assert float(csv_row[k]) == value
        details.append(dict(key=key, generated=raw['generated_payload_bits'],
                            delivered=raw['delivered_payload_bits'],
                            dropped=raw['dropped_payload_bits'],
                            backlog=raw['backlog_payload_bits']))
    images = {}
    for name in ARTIFACTS[2:]:
        with Image.open(folder / name) as im:
            assert im.format == 'PNG'
            im.verify()
        with Image.open(folder / name) as im:
            im.load()
            assert min(im.size) > 100
            images[name] = list(im.size)
    current = hashes(folder)
    if repeat is not None:
        assert current == hashes(repeat), 'Repeated artifacts differ'
    return dict(status='passed', config=asdict(cfg), rows=8, traces=8,
                conservation=details, images=images, sha256=current,
                repeat_identical=repeat is not None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeat', type=Path)
    args = parser.parse_args()
    result = verify(ROOT / 'results', args.repeat)
    path = ROOT / 'results/logs/05_artifact_verification.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

"""Vary only header_bits through existing interfaces; preserve baseline files."""
import csv
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.build/matplotlib'))

from src.metrics import summarize
from src.models import Config
from src.performance_test import SCENARIOS
from src.utils import make_traffic, simulate
from scripts.verify_baseline import hashes


def run():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output = ROOT / 'results/extra'
    output.mkdir(parents=True, exist_ok=True)
    original_hashes = hashes(ROOT / 'results')
    baseline = json.loads((ROOT / 'results/comparison.json').read_text(encoding='utf-8'))
    default = Config()
    seed = 2026
    traffic = {s: make_traffic(s, default, seed) for s in SCENARIOS}
    arrival_sha256 = {
        s: hashlib.sha256(json.dumps([asdict(a) for a in arrivals], sort_keys=True)
                          .encode('utf-8')).hexdigest()
        for s, arrivals in traffic.items()
    }
    runs = []
    flat_rows = []
    for header_bits in (0, 32, 64):
        cfg = replace(default, header_bits=header_bits)
        rows, traces = [], {}
        for scenario in SCENARIOS:
            assert traffic[scenario] == make_traffic(scenario, cfg, seed)
            for mode in ('circuit', 'packet'):
                raw = simulate(traffic[scenario], cfg, mode)
                metrics = summarize(raw, cfg)
                row = dict(scenario=scenario, mode=mode, **metrics)
                rows.append(row)
                flat_rows.append(dict(header_bits=header_bits, **row))
                traces[f'{scenario}/{mode}'] = raw
        if header_bits == default.header_bits:
            assert rows == baseline['rows'] and traces == baseline['traces']
        runs.append(dict(config=asdict(cfg), seed=seed, rows=rows, traces=traces))
    # Circuit service does not use packet headers; every raw counter must match.
    for scenario in SCENARIOS:
        key = f'{scenario}/circuit'
        assert all(r['traces'][key] == runs[0]['traces'][key] for r in runs)

    obj = dict(varied_parameter='header_bits', values=[0, 32, 64], seed=seed,
               arrival_sha256=arrival_sha256, runs=runs,
               baseline_sha256=original_hashes)
    (output / 'header_sweep.json').write_text(
        json.dumps(obj, indent=2), encoding='utf-8')
    with (output / 'header_sweep.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    fig, axes = plt.subplots(2, 4, figsize=(15, 7), layout='constrained')
    for col, scenario in enumerate(SCENARIOS):
        for mode, color, marker in (('circuit', '#27638b', 'o'),
                                     ('packet', '#d27a35', 's')):
            data = [r for r in flat_rows if r['scenario'] == scenario and r['mode'] == mode]
            for row_idx, metric in enumerate(('payload_utilization', 'mean_delay_ms')):
                ax = axes[row_idx, col]
                ax.plot([r['header_bits'] for r in data], [r[metric] for r in data],
                        label=mode, color=color, marker=marker)
                ax.set_xticks([0, 32, 64])
                ax.grid(alpha=.25)
                if row_idx == 0:
                    ax.set_title(scenario)
                else:
                    ax.set_xlabel('Header per record (bits)')
                if col == 0:
                    ax.set_ylabel('Payload utilization' if row_idx == 0
                                  else 'Mean completion delay (ms)')
        axes[0, col].legend()
    fig.suptitle('Header-only experiment: same arrivals, 256 ticks, no draining')
    fig.savefig(output / 'header_sweep.png', dpi=150)
    plt.close(fig)
    assert hashes(ROOT / 'results') == original_hashes, 'Baseline was modified'
    from PIL import Image
    with Image.open(output / 'header_sweep.png') as im:
        im.verify()
    with (output / 'header_sweep.csv').open(encoding='utf-8-sig', newline='') as f:
        assert len(list(csv.DictReader(f))) == 24
    print('Generated 3 full configurations, 24 metrics rows and 24 traces in results/extra')
    print('Same arrivals across headers and modes; default case matches baseline; baseline hashes unchanged')
    for row in flat_rows:
        if row['mode'] == 'packet':
            print(json.dumps(row))


if __name__ == '__main__':
    run()

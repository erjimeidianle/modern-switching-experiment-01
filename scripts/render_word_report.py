"""Use existing Microsoft Word for PDF, then the packaged render_docx PNG pipeline.

Windows runtime has no bundled LibreOffice. This adapter does not modify the
managed renderer or use system LibreOffice; it replaces only PDF conversion
with the installed Word API and keeps canonical rasterization and page naming.
"""
import argparse
import importlib.util
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--canonical-renderer', required=True, type=Path)
    args = parser.parse_args()
    source = ROOT / 'reports/实验一报告_郑航宇_2024280087.docx'
    cache = ROOT / '.build/word_report/native'
    cache.mkdir(parents=True, exist_ok=True)
    pdf = cache / 'word_report.pdf'
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'scripts/render_word_report.ps1'),
                    '-InputDocx', str(source), '-OutputPdf', str(pdf)], check=True)
    assert pdf.is_file() and pdf.stat().st_size > 1000
    spec = importlib.util.spec_from_file_location('canonical_docx_renderer', args.canonical_renderer)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)

    def native_pdf_conversion(*unused_args, **unused_kwargs):
        return str(pdf), 'Rendered by installed Microsoft Word; canonical PNG rasterization follows.'

    renderer.convert_to_pdf = native_pdf_conversion
    pages = renderer.rasterize(str(source), str(ROOT / '.build/word_report/render'),
                               dpi=150, verbose=False, emit_pdf=True)
    print('Inspected document renderer input:', source)
    print('Rendered pages:', len(pages))
    print('\n'.join(pages))


if __name__ == '__main__':
    main()

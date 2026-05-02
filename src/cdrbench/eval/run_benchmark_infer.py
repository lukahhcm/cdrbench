#!/usr/bin/env python3
from __future__ import annotations

import argparse

from cdrbench.eval.benchmark_eval_shared import add_infer_args, run_infer_cli


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run CDR-Bench inference on eval-ready JSONL and save raw predictions.'
    )
    add_infer_args(parser)
    args = parser.parse_args()
    run_infer_cli(args)


if __name__ == '__main__':
    main()

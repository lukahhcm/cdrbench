#!/usr/bin/env python3
from __future__ import annotations

import argparse

from cdrbench.eval.benchmark_eval_shared import add_score_args, run_score_cli


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Score CDR-Bench predictions and write reports.'
    )
    add_score_args(parser)
    args = parser.parse_args()
    run_score_cli(args)


if __name__ == '__main__':
    main()

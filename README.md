# ICDR-Bench

这份仓库用于下载 ICDR-Bench 的已整理 JSONL 数据，并继续做 Data-Juicer 打标。

## 1. 拉代码

```bash
git clone https://github.com/lukahhcm/icdrbench.git
cd icdrbench
```

## 2. 拉 Data-Juicer 并配置环境

先单独拉一份 `data-juicer`：

```bash
git clone https://github.com/datajuicer/data-juicer.git /path/to/data-juicer
export ICDRBENCH_DATA_JUICER_ROOT=/path/to/data-juicer
```

再创建 Python 环境并安装当前项目：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
python -m pip install -U huggingface_hub py-data-juicer
```

如果 `data-juicer` 就放在仓库根目录下的 `./data-juicer`，可以不设 `ICDRBENCH_DATA_JUICER_ROOT`。

## 3. 下载数据

从 Hugging Face 下载当前 manifest 里的 JSONL：

```bash
HF_TOKEN=<your_hf_token_if_needed> \
python scripts/release/download_hf_jsonl.py \
  --repo-id lukahh/icdrbench-raw \
  --repo-root .
```

默认会下载这些文件到 `data/raw/`：

- `arxiv/arxiv-4k.jsonl`
- `commoncrawl/cc-10k.jsonl`
- `enwiki/enwiki-pages-110k.jsonl`
- `govreport/govreport-20k.jsonl`
- `pii/pii-43k.jsonl`
- `pii/docpii-contextual-1k.jsonl`
- `pii/synthetic-anonymizer-8k.jsonl`

## 4. 继续打标

先小规模试跑：

```bash
PYTHONPATH=src python scripts/prepare_data/tag_and_assign_domains.py --max-records 200
```

正式继续跑：

```bash
PYTHONPATH=src python scripts/prepare_data/tag_and_assign_domains.py --resume
```

输出文件：

- `data/processed/domain_tags/*.jsonl`
- `data/processed/domain_filtered/*.jsonl`
- `data/processed/domain_filtered/all.jsonl`
- `outputs/domain_operator_catalog.csv`
- `outputs/domain_labeling_summary.csv`
- `outputs/domain_assignment_counts.csv`

## 常用补充

只跑部分语料：

```bash
PYTHONPATH=src python scripts/prepare_data/tag_and_assign_domains.py --corpora arxiv pii --resume
```

如果要跑 Data-Juicer 单算子 probe：

```bash
PYTHONPATH=src python scripts/prepare_data/run_dj_per_op_probe.py --execute --resume
```

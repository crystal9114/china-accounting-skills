# qsys — 自用量化系统（开源拼装）

进度慢通常不是因为「回测引擎没写完」，而是把数据、研究、风控、模拟盘、看板一起从零造。这套东西**不发明新引擎**，只把已经稳定的开源库接到一条能跑的流水线上。

自用、非商用。不是券商、不是投顾，也不能当实盘交易软件。

## 拼了什么

| 你要的能力 | 用的开源项目 | 本仓库做的事 |
|---|---|---|
| 美股/ETF 行情 | [yfinance](https://github.com/ranaroussi/yfinance)（可选） | 适配器 + 本地缓存 |
| A 股日线 | [AKShare](https://github.com/akfamily/akshare)（可选） | 适配器 + 前复权参数 |
| 加密行情 | [ccxt](https://github.com/ccxt/ccxt)（可选） | 适配器 |
| 本地数据湖 | parquet / [pyarrow](https://arrow.apache.org/) | 按 source/symbol 落盘、增量合并 |
| 回测 | 内置向量化权重引擎（信号隔日生效，避免未来函数） | 薄封装；需要极速参数扫描时再自己接 vectorbt |
| 绩效报告 | 内置指标；可选 [QuantStats](https://github.com/ranaroussi/quantstats) HTML tearsheet | 写到 `var/reports/` |
| 组合约束 | 最大权重 / 总敞口 / 现金垫 | `qsys.portfolio` |
| 模拟盘 | SQLite 账本（持仓、成交、权益） | `qsys paper` |
| 看板 | [Streamlit](https://streamlit.io/)（可选） | `qsys dashboard` |
| 命令行 | [Typer](https://typer.tiangolo.com/) | `qsys` |

没有把 [Fincept Terminal](https://github.com/Fincept-Corporation/FinceptTerminal) 整仓搬进来：那是 C++/Qt 巨型终端，AGPL，开源版还在降频维护。自用量化该复用的是 **yfinance / AKShare / ccxt / QuantStats** 这些内核，不是整台终端。

以后若要接国内券商柜台，优先看 [vn.py / VeighNa](https://github.com/vnpy/vnpy)，不要在这个研究栈里塞交易网关。

## 流水线

```
行情源 ──► parquet 数据湖 ──► 策略(目标权重)
                                │
                     ┌──────────┴──────────┐
                     ▼                     ▼
                   回测 + 报告           模拟盘账本
                     │                     │
                     └────────► Streamlit ─┘
```

策略只输出**目标权重**（每列一个标的）。回测默认把 `t` 日收盘算出来的权重，挪到 **下一根 K 线** 再生效，避免用当天收益成交。

内置策略：

- `sma` — 均线金叉等权做多
- `momentum` — 过去 N 日收益 Top-K
- `mean_reversion` — 窗口 z-score 超卖做多
- `equal_weight` — 基准：有价格就等权

## 安装

需要 Python 3.11+。

```bash
cd quant
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

按市场加可选依赖：

```bash
pip install -e ".[us]"       # yfinance
pip install -e ".[china]"    # akshare
pip install -e ".[crypto]"   # ccxt
pip install -e ".[report]"   # quantstats 报告
pip install -e ".[ui]"       # streamlit 看板
```

## 五分钟跑通

```bash
qsys demo
```

会用**合成行情**（不访问任何交易所）完成：拉数 → 回测 → 写报告 → 模拟盘一步。

常用命令：

```bash
qsys data pull                          # 按 configs/default.yaml 拉数
qsys data status
qsys backtest run --strategy sma
qsys backtest walk-forward --train 252 --test 63
qsys paper step
qsys paper status
qsys dashboard                          # 需要 qsys[ui]
```

改宇宙和策略：编辑 [`configs/default.yaml`](configs/default.yaml)。

### 换成真实行情

美股（先 `pip install -e ".[us]"`）：

```yaml
universe:
  source: yfinance
  symbols: [SPY, QQQ, AAPL]
  start: "2018-01-01"
```

A 股（先 `pip install -e ".[china]"`，代码用 6 位）：

```yaml
universe:
  source: akshare
  symbols: ["000001", "600519", "000858"]
  start: "2018-01-01"
  adjust: qfq
```

加密（先 `pip install -e ".[crypto]"`）：

```yaml
universe:
  source: ccxt
  symbols: ["BTC/USDT", "ETH/USDT"]
data:
  ccxt_exchange: binance
  ccxt_timeframe: 1d
```

然后：

```bash
qsys data pull
qsys backtest run --strategy momentum
```

## 自己加策略

实现 `generate(close) -> DataFrame`，权重列对齐标的、索引对齐日期，只用到当天及以前的价格：

```python
from qsys.strategy import Strategy, STRATEGIES

class MyStrat(Strategy):
    name = "my_strat"

    def generate(self, close):
        mom = close.pct_change(self.params.get("lookback", 20))
        picked = mom.gt(0).astype(float)
        n = picked.sum(axis=1).replace(0, 1.0)
        return picked.div(n, axis=0).fillna(0.0)

STRATEGIES[MyStrat.name] = MyStrat
```

把类登记进 `qsys/strategy.py` 的 `STRATEGIES` 后即可 `--strategy my_strat`。

## 测试

```bash
cd quant
pytest
```

测试全部走合成数据，不访问外网。

## 刻意没做的事

- 国内股票真实下单（券商柜台 / 券商 API）
- 盘口、逐笔、期货保证金、期权希腊值
- 点-in-time 基本面、幸存者偏差处理
- 把 vectorbt 做成硬依赖（安装重，且带 Commons Clause，不适合当默认内核）

这些要做的时候，在现有 `Strategy` / `ParquetLake` 边界上加 provider，而不是重写整条流水线。

## 许可

本目录代码随仓库 MIT。第三方库各自有许可证：yfinance / AKShare / ccxt / QuantStats 多为 Apache-2.0 或 Apache 风格；vectorbt 若你另行安装，是 Apache-2.0 + Commons Clause，不能拿它当主要产品去卖。

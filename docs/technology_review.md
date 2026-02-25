# Trade Rewind: Technology Review 

---

## 1. Background & Motivation

Trade Rewind is a backtesting application that lets users explore historical stock trading strategies (Moving Average Crossover, Mean Reversion) and evaluate their performance through professional-grade metrics such as Sharpe Ratio and Max Drawdown. Users interact with the app through a web interface, and receive visual output and downloadable results for comparison.

Building this application requires decisions across three distinct technical areas: the **user interface framework**, the **data manipulation and computation libraries**, and the **visualization engine**. This document reviews candidate libraries in each area, explains why specific choices were made over alternatives, and identifies known drawbacks.

---

## 2. Library Reviews by Category

---

### 2.1 User Interface Framework

The UI layer needs to render charts, accept user inputs (strategy parameters, date ranges, stock selection), and display results tables - all without requiring the team to write and maintain custom HTML/CSS/JavaScript.

#### Candidate: Streamlit
- **Author:** Streamlit Inc. (acquired by Snowflake, 2022)
- **License:** Apache 2.0
- **Summary:** Streamlit turns a plain Python script into an interactive web application. Widgets like sliders, dropdowns, and file uploaders are declared in a single line of Python. There is no separation between frontend and backend code - the same script handles both. Streamlit renders in the browser but requires no web development knowledge.

#### Candidate: Flask
- **Author:** Armin Ronacher / Pallets Project
- **License:** BSD 3-Clause
- **Summary:** A lightweight Python web framework that gives full control over routing, templates (Jinja2), and HTTP handling. Building a comparable UI to Streamlit in Flask requires writing HTML templates, handling form submissions manually, and managing state between requests. It is far more powerful but significantly more work.

#### Candidate: Gradio
- **Author:** Gradio / Hugging Face
- **License:** Apache 2.0
- **Summary:** Like Streamlit, Gradio lets you build web UIs in pure Python. It was originally designed for machine learning model demos and is optimized for single-input/single-output interfaces. Its layout flexibility and support for complex multi-panel apps with financial data tables and strategy comparison views is more limited than Streamlit.

#### Comparison

| Criterion | Streamlit | Flask | Gradio |
|---|---|---|---|
| **Setup complexity** | Minimal - one script | High - routes, templates, static files | Minimal |
| **Python-only development** | Yes | No - requires HTML/Jinja2 | Yes |
| **Layout flexibility** | Moderate | Full | Limited |
| **Data table display** | `st.dataframe()` built-in | Manual HTML rendering | Limited |
| **Chart integration** | Native Plotly & Matplotlib support | Manual embedding | Basic |
| **Multi-page support** | Yes (native) | Yes | Limited |
| **Best suited for** | Data apps, dashboards | Full web applications | ML demos |

#### Final Choice: Streamlit

Streamlit is chosen because the team's focus is on backtesting logic and financial analysis, not web development. It provides built-in components for everything Trade Rewind needs - data tables, file upload, sidebar controls, and chart rendering - with no HTML or JavaScript required. Flask would require maintaining a separate frontend layer that adds complexity without benefit for this scope. Gradio's limited layout options make it unsuitable for a multi-panel dashboard displaying strategy results, equity curves, and metrics side by side.

---

### 2.2 Data Manipulation & Computation

The backtesting engine must load historical OHLCV data, compute rolling indicators (moving averages, RSI), simulate trade execution over time, and calculate portfolio metrics like Sharpe Ratio and Max Drawdown. Two libraries are central to this.

#### Candidate: Pandas
- **Author:** Wes McKinney (now maintained by the Pandas Development Team / NumFOCUS)
- **License:** BSD 3-Clause
- **Summary:** Pandas provides the `DataFrame` - a labeled, two-dimensional table structure that maps directly onto how financial time series data is naturally shaped: rows are dates, columns are price fields (Open, High, Low, Close, Volume). It supports date-aware indexing, rolling window calculations (`rolling().mean()`), boolean filtering for trade signals, and direct CSV import. The `st.dataframe()` Streamlit widget accepts a Pandas DataFrame directly, making the path from raw data to displayed results table seamless.

#### Candidate: NumPy
- **Author:** Travis Oliphant (now maintained by the NumPy Development Team / NumFOCUS)
- **License:** BSD 3-Clause
- **Summary:** NumPy provides the N-dimensional array (`ndarray`) and the mathematical operations that run on it. It is the computational foundation that Pandas is built on. For Trade Rewind, NumPy is used directly in `metrics.py` to implement Sharpe Ratio, annualized return, and Max Drawdown calculations - operations more naturally expressed as array math than as DataFrame operations. NumPy's vectorized operations also make these calculations significantly faster than Python loops over the same data.

#### Why not use a dedicated math library (e.g., SciPy, TA-Lib)?

SciPy and TA-Lib offer pre-built financial indicator and statistics functions. However, the metrics Trade Rewind requires (Sharpe Ratio, drawdown, returns) are simple enough to implement in a few lines of NumPy. Adding SciPy introduces a large dependency for minimal gain. TA-Lib requires a C binary installation that complicates deployment. NumPy and Pandas together provide all necessary functionality without additional dependencies.

#### Comparison

| Criterion | Pandas | NumPy |
|---|---|---|
| **Primary use in project** | Data loading, time series management, trade logs, results tables | Metric calculations (Sharpe, drawdown, returns) |
| **Data structure** | DataFrame (labeled rows/columns, date index) | ndarray (unlabeled, fast numerical arrays) |
| **CSV import** | `pd.read_csv()` - one line | Not designed for this |
| **Rolling indicators** | `df['MA20'] = df['Close'].rolling(20).mean()` | Requires manual implementation |
| **Vectorized math** | Supported, but slower than NumPy for pure computation | Core strength |
| **Streamlit display** | `st.dataframe(df)` - native | Not directly displayable |

Pandas and NumPy are complementary rather than competing. Pandas handles everything involving labeled data and time series structure; NumPy handles the numerical computation layer underneath. Both are required.

---

### 2.3 Visualization Engine

#### Candidate: Matplotlib
- **Author:** John D. Hunter (now maintained by the Matplotlib Development Team)
- **Version reviewed:** 3.10.8 *(installed and tested)*
- **License:** BSD-style
- **Summary:** The foundational Python plotting library. Provides full control over figure elements and outputs static images (PNG, PDF, SVG). Integrates with Streamlit via `st.pyplot()`. Best suited for PDF report generation. Render time in testing: ~0.17s for a 100-point line chart.

#### Candidate: Seaborn
- **Author:** Michael Waskom
- **Version reviewed:** 0.13.2
- **License:** BSD 3-Clause
- **Summary:** A statistical visualization library built on Matplotlib with cleaner defaults and less boilerplate. Static output only. Render time in testing: ~0.12s for the same chart.

#### Candidate: Plotly
- **Author:** Plotly Technologies Inc.
- **Version reviewed:** 5.x (latest stable)
- **License:** MIT
- **Summary:** Interactive, browser-based charting with built-in zoom, pan, and hover tooltips. Streamlit has first-class support via `st.plotly_chart()`. Required for user-driven exploration of equity curves and drawdown periods.

#### Comparison

| Criterion | Matplotlib | Seaborn | Plotly |
|---|---|---|---|
| **Interactivity** | None (static) | None (static) | Full (zoom, pan, hover tooltips) |
| **Streamlit integration** | `st.pyplot()` | `st.pyplot()` | `st.plotly_chart()` - native |
| **PDF report export** | Native | Native (via Matplotlib) | Requires `kaleido` dependency |
| **Render time (100-pt line)** | ~0.17s | ~0.12s | ~0.3–0.5s (browser render) |
| **Default aesthetics** | Minimal | Clean | Polished, modern |
| **Large dataset performance** | Good | Good | Degrades above ~50k points |

#### Final Choice: Plotly (primary) + Matplotlib (PDF reports only)

Plotly is the primary charting library for all in-app visualizations because Trade Rewind is an exploratory tool - users need to zoom into drawdown periods, hover for exact values, and compare strategies visually. Static charts cannot support this workflow. Matplotlib is retained only for PDF report generation where HTML/JS output is not applicable. Seaborn is not included as it provides no capability beyond Matplotlib for this project's needs.

---

## 3. Final Tech Stack Summary

| Layer | Library | Rationale |
|---|---|---|
| **User Interface** | Streamlit | Python-only; no HTML/JS required; built-in widgets and data table display |
| **Data Management** | Pandas | DataFrame maps naturally to time series; rolling indicators; CSV import; Streamlit-native display |
| **Computation** | NumPy | Fast vectorized math for Sharpe Ratio, drawdown, and return calculations |
| **In-app Charts** | Plotly | Interactive zoom/pan/hover; native Streamlit support |
| **Report Charts** | Matplotlib | Native static image/PDF output for embedded reports |
| **PDF Reports** | ReportLab / FPDF | Programmatic PDF generation |
| **Testing** | unittest | Standard library; no additional dependency |

---

## 4. Drawbacks & Areas of Concern

**Streamlit:** Stateless by default - every user interaction reruns the entire script. For computationally heavy backtests this can cause slow or unresponsive behavior. Mitigation: use `@st.cache_data` to cache backtest results and avoid redundant recalculation.

**Plotly:** Performance degrades with datasets above ~50,000 points. Daily OHLCV data across a few years is well within safe limits, but intraday data would be a risk. PDF export requires the `kaleido` binary which can have version compatibility issues - Matplotlib is used instead for all report output. The JavaScript bundle (~3 MB) adds initial page-load latency.

**Pandas:** Memory usage scales with dataset size. Loading many stocks simultaneously could become a concern. For the current scope of individual CSV files per stock this is not an issue.

**Matplotlib (secondary role):** Static-only output means it cannot be used for in-app interaction. Its role is intentionally limited to `reports.py`.

**Mixing Plotly + Matplotlib:** Maintaining two charting libraries adds overhead. This is mitigated by strict module separation: `reports.py` uses Matplotlib exclusively; all other chart code uses Plotly.

---

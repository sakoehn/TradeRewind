**Trade Rewind: Simple Application Architecture**

**Background**

- We want users to be able to understand various stock trading strategies through backtesting historical stock market data, and then analyzing its performance through professional grade metrics. The user will be able to see their choices through visualizations as well as download a table of results from all their trading tradies and metrics with the purpose of comparison.  

**Description of 2-3 python libraries (name, author, summary)**

1. **Pandas by Wes McKinney**  
   Pandas is a Python library used for data manipulation and analysis. We will use Pandas to organize and manipulate stock market data. It will make it easier for us to create and filter dataframes of specific stocks and date ranges.  
2. **Plotly by Plotly Technologies Inc. (Alex Johnson, Jack Parmer, Chris Parmer, and Matthew Sundquist)**  
   Plotly is a Python visualization library used for interactive charts. We will use Plotly for interactive line graphs that will allow users to hover over and zoom into stock price data and strategy results.  
3. **Streamlit by Streamlit Inc. (Adrien Treuille, Thiago Teixeira, and Amanda Kelly)**  
   Streamlit is a Python framework used for building web applications for data projects. We will use Streamlit for the user interface because it will allow us to create an interactive application with less code complexity.

**Comparisons:**

**Front end:**

| Library | Considered | Decision | Notes |
| :---- | :---- | :---- | :---- |
| Streamlit | Yes | Will Use | Provides an easier way to build interactive user interface with less code complexity |
| Flask | Yes | Will not Use | Provides more flexibility but requires more setup compared to Streamlit. |
| HTML/CSS | Yes | Will not Use | Could be used, but adds additional frontend complexity and requires many lines of code. |

**Data:**

| Library | Considered | Decision | Notes |
| :---- | :---- | :---- | :---- |
| Pandas | Yes | Will Use | Best for handling tabular data like ours. This is because it will need to be filtered and manipulated. |
| NumPy | Yes | Will Use | Best for numerical calculations like the metrics we are hoping to implement. |
| Python math | Yes | Will not Use | NumPy already provides the needed mathematical functions and works better with larger datasets. |
| SciPy | Yes | Will not Use | Considered, but given that numpy will be enough for the calculations we want to do, it will not be necessary.  |

**Visualization:**

| Library | Considered | Decision | Notes |
| :---- | :---- | :---- | :---- |
| Plotly | Yes | Will Use | Best for interactive charts with hovering and zooming options which we want for our stock data charts. |
| Matplotlib | Yes | Will Use | Great for static charts but not the kind of interactive charts we want. We might still use for pyplot.table function to draw the metrics table |
| Seaborn | Yes | Considered | Good statistical visualizations but still static.   |

**Reports:**

| Library | Considered | Decision | Notes |
| :---- | :---- | :---- | :---- |
| ReportLab | Yes | Will Use | Best for visualizing heavy files like the ones we will get from our charts. |
| FPDF | Yes | Will not Use | This one is best for word heavy PDFs yet ours will be more visualization heavy. |

**Testing**

| Library | Considered | Decision | Notes |
| :---- | :---- | :---- | :---- |
| unittest | Yes | Will Use | Offers a testing framework sufficient for our project. |

**Final Choice:** 

**Tech Stack:**  
**Frontend:**  Streamlit   
**Backend:**   Python (pandas, numpy)  
**Data:**      Local CSV files (individual stocks) \+ FRED \+ Kaggle (when decided)  
**Charts:**    Plotly and Matplotlib   
**Reports:**   ReportLab  
**Testing:** unittest

**Tech Stack Use Description:**

- **Pandas:**  
  We will use Pandas to organize and manipulate stock market data. It will make it easier for us to create and filter dataframes of specific stocks and date ranges.  
- **NumPy:**  
  We will use NumPy for calculations such as returns and drawdowns.  
- **Plotly:**  
  We will use Plotly for interactive line graphs that will allow users to hover over and zoom into data points.  
- **Matplotlib:**  
  We considered using Matplotlib to supplement plotly especially for the metrics table. This is because Matplotlib is good with static graphs and has a pyplot.table function we can use for table visualization.   
- **Seaborn:**  
  We considered using Seaborn for visualizations, but since we plan to use Plotly we likely will not use it in the final implementation.  
- **Streamlit:**  
  We will use Streamlit for the user interface because it will allow us to create an interactive application with less code complexity.  
- **Unittest:**  
  We will use unittest to ensure that our code is running correctly and that we are covering edge cases.

**File Structure:**

traderewind/  
├── app.py                      \# Main web app  
├── strategies/  
│   ├── moving\_average.py       \# MA Crossover strategy  
│   ├── mean\_reversion.py       \# Mean reversion strategy  
│   └── rsi\_strategy.py         \# RSI strategy  
├── backtester.py               \# Core backtesting engine  
├── metrics.py                  \# Sharpe, drawdown calculations  
├── reports.py                  \# PDF report generator  
├── data/  
│   └── stocks/  
│       ├── AAPL.csv  
│       ├── MSFT.csv  
│       └── …...  
└── templates/  
    ├── home.html  
    ├── results.html  
    └── info.html


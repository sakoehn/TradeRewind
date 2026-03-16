"""TradeRewind Streamlit app launcher.

Running this script starts Streamlit with home_page.py as the main page,
so the sidebar shows only Home and the other pages (no app.py entry).
Usage: python app.py   or   streamlit run home_page.py
"""

import subprocess
import sys

if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "home_page.py", *sys.argv[1:]],
        check=True,
    )

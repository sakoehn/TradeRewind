import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def strategy_dashboard(df, summary, initial_capital):

    df = df.copy()
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df = df.dropna(subset=['daily_value', 'daily_returns'])

    # Cleaning up some values
    formatted_summary = {}
    for k, v in summary.items():
        if isinstance(v, float):
            if "return" in k.lower() or "%" in k:
                formatted_summary[k] = f"{v*100:.2f}%"
            else:
                formatted_summary[k] = f"{v:.2f}"
        else:
            formatted_summary[k] = str(v)

    
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.7, 0.3],
        specs=[[{"type": "scatter"}, {"type": "domain"}]], 
        horizontal_spacing=0.05
    )

    # Adding the line graphs
    columns_to_plot = ['daily_value', 'daily_returns', 'profit_to_date', 'drawdown']
    available_cols = [col for col in columns_to_plot if col in df.columns]

    for col in available_cols:
        if col == 'daily_returns':
            hover_fmt = f'{col}: %{{y:.4f}}<br>Date: %{{x}}<extra></extra>'
        else:
            hover_fmt = f'{col}: %{{y:.2f}}<br>Date: %{{x}}<extra></extra>'
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df[col],
                mode='lines',
                name=col,
                hovertemplate=hover_fmt
            ),
            row=1, col=1
        )
    # Highlighting peak value
    if 'daily_value' in df.columns and not df.empty:
        max_idx = df['daily_value'].idxmax()
        fig.add_trace(
            go.Scatter(
                x=[df['date'][max_idx]],
                y=[df['daily_value'][max_idx]],
                mode='markers+text',
                marker=dict(size=12, color='red'),
                text=['Peak Portfolio'],
                textposition='top center',
                name='Peak Value'
            ),
            row=1, col=1
        )

    # Highlighting max drawdown
    if 'drawdown' in df.columns and not df.empty:
        min_idx = df['drawdown'].idxmin()
        fig.add_trace(
            go.Scatter(
                x=[df['date'][min_idx]],
                y=[df['daily_value'][min_idx]],
                mode='markers+text',
                marker=dict(size=12, color='black'),
                text=['Max Drawdown'],
                textposition='bottom center',
                name='Max Drawdown'
            ),
            row=1, col=1
        )

    # Adding an initial capital line
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="green",
        annotation_text="Initial Capital",
        annotation_position="bottom right",
        row=1, col=1
    )

    # Metrics table
    fig.add_trace(
        go.Table(
            header=dict(values=["Metric", "Value"],
                        fill_color='lightgrey',
                        align='left'),
            cells=dict(
                values=[list(formatted_summary.keys()), list(formatted_summary.values())],
                align='left'
            )
        ),
        row=1, col=2
    )

    fig.update_layout(
        title="Strategy Performance Over Time",
        template="plotly_white",
        hovermode='x unified',
        showlegend=True
    )

    fig.show()
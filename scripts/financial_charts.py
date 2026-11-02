"""Biểu đồ tài chính: chỉ vẽ điểm hợp lệ, giữ năm thiếu và đúng mốc năm."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

COMPANY_COLOR = '#4F9E1E'
PEER_COLOR = '#C07820'
PEER_BAR_COLOR = '#AAB9A0'


def numeric_values(values):
    s = pd.to_numeric(pd.Series(values, dtype='object'), errors='coerce')
    return s.where(np.isfinite(s))


def has_numeric_data(fig):
    return fig is not None and any(
        numeric_values(trace.y).notna().any()
        for trace in fig.data if getattr(trace, 'y', None) is not None)


def clean_figure(fig, periods=None):
    """Bỏ đường rỗng; năm là nhãn rời rạc, không sinh mốc 2021,5."""
    fig.data = tuple(t for t in fig.data if getattr(t, 'y', None) is not None
                     and numeric_values(t.y).notna().any())
    if not fig.data:
        return None
    seen_groups = set()
    for trace in fig.data:
        if trace.legendgroup:
            trace.showlegend = trace.legendgroup not in seen_groups
            seen_groups.add(trace.legendgroup)
    if periods is not None:
        labels = list(dict.fromkeys(str(p) for p in periods))
        fig.update_xaxes(type='category', categoryorder='array', categoryarray=labels,
                         tickmode='array', tickvals=labels, ticktext=labels)
    return fig


def history_figure(history, ticker, title, scale=1, unit=''):
    fig = go.Figure()
    if history is None or history.empty:
        return None
    labels = history.DisplayPeriod.astype(str).tolist()
    for column, name, color, dash in [('Value', ticker, COMPANY_COLOR, 'solid'),
                                      ('PeerMean', 'Bình quân peer cùng kỳ', PEER_COLOR, 'dash')]:
        if column not in history:
            continue
        values = numeric_values(history[column].tolist())
        if column == 'Value' and 'Status' in history:
            values = values.where(history.Status.reset_index(drop=True).eq('OK'))
        points = [float(v * scale) if pd.notna(v) else None for v in values]
        fig.add_trace(go.Scatter(x=labels, y=points, name=name, mode='lines+markers',
                                connectgaps=False, line=dict(color=color, dash=dash)))
    fig.update_layout(title=title, height=330, legend=dict(orientation='h', y=-.2),
                      margin=dict(t=50, b=70), yaxis_title=unit)
    return clean_figure(fig, labels)


def peer_figure(frame, ticker, title, scale=1, unit=''):
    if frame is None or frame.empty:
        return None
    q = frame.reset_index(drop=True).copy()
    q['Value'] = numeric_values(q.Value.tolist())
    q = q.dropna(subset=['Value'])
    if q.empty:
        return None
    fig = go.Figure(go.Bar(x=q.Ticker.tolist(), y=(q.Value * scale).tolist(),
                          marker_color=[COMPANY_COLOR if t == ticker else PEER_BAR_COLOR for t in q.Ticker]))
    peers = q.loc[q.Ticker.ne(ticker), 'Value']
    if len(peers) >= 5:
        fig.add_hline(y=float(peers.mean() * scale), line_dash='dash', line_color=PEER_COLOR,
                      annotation_text='Bình quân peer', annotation_position='top right')
    fig.update_layout(title=title, height=330, margin=dict(t=55, b=45), yaxis_title=unit)
    fig.update_xaxes(type='category')
    return fig

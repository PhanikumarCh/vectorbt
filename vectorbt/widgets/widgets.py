"""A collection of custom Plotly widgets."""

import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt

from vectorbt.widgets.common import UpdatableFigureWidget, FigureWidget
from vectorbt.utils import checks, reshape_fns
from collections import namedtuple


# ############# Indicator ############# #


def rgb_from_cmap(cmap_name, value, value_range):
    """Map `value_range` to colormap and get RGB of the value from that range."""
    if value_range[0] == value_range[1]:
        norm_value = 0.5
    else:
        norm_value = (value - value_range[0]) / (value_range[1] - value_range[0])
    cmap = plt.get_cmap(cmap_name)
    return "rgb(%d,%d,%d)" % tuple(np.round(np.asarray(cmap(norm_value))[:3] * 255))


class Indicator(UpdatableFigureWidget):
    def __init__(self, value=None, label=None, value_range=None, cmap_name='Spectral', trace_kwargs={}, **layout_kwargs):
        """Create an updatable indicator plot.

        Args:
            value (int or float, optional): The value to be displayed.
            label (str, optional): The label to be displayed.
            value_range (list or tuple of 2 values, optional): The value range of the gauge.
            cmap_name (str, optional): A matplotlib-compatible colormap name, see the [list of available colormaps](https://matplotlib.org/tutorials/colors/colormaps.html).
            trace_kwargs (dict, optional): Keyword arguments passed to the [`plotly.graph_objects.Indicator`](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Indicator.html).
            **layout_kwargs: Keyword arguments for layout.
        Examples:
            ```py
            vbt.Indicator(value=2, value_range=(1, 3), label='My Indicator')
            ```
            ![](img/Indicator.png)
            """

        self._value_range = value_range
        self._cmap_name = cmap_name

        super().__init__()
        self.update_layout(width=500, height=300)
        self.update_layout(**layout_kwargs)

        # Add traces
        indicator = go.Indicator(
            domain=dict(x=[0, 1], y=[0, 1]),
            mode="gauge+number+delta",
            title=dict(text=label)
        )
        indicator.update(**trace_kwargs)
        self.add_trace(indicator)

        if value is not None:
            self.update_data(value)

    def update_data(self, value):
        """Update the data of the plot efficiently.

        Args:
            value (int or float): The value to be displayed.
        """
        # NOTE: If called by Plotly event handler and in case of error, this won't visible in a notebook cell, but in logs!
        checks.assert_type(value, (int, float))

        # Update value range
        if self._value_range is None:
            self._value_range = value, value
        else:
            self._value_range = min(self._value_range[0], value), max(self._value_range[1], value)

        # Update traces
        with self.batch_update():
            indicator = self.data[0]
            if self._value_range is not None:
                indicator.gauge.axis.range = self._value_range
                if self._cmap_name is not None:
                    indicator.gauge.bar.color = rgb_from_cmap(self._cmap_name, value, self._value_range)
            indicator.delta.reference = indicator.value
            indicator.value = value

# ############# Bar ############# #


class Bar(UpdatableFigureWidget):

    def __init__(self, x_labels, trace_names=None, data=None, trace_kwargs={}, **layout_kwargs):
        """Create an updatable bar plot.

        Args:
            x_labels (list of str): X-axis labels, corresponding to index in pandas.
            trace_names (str or list of str, optional): Trace names, corresponding to columns in pandas.
            data (array_like, optional): Data in any format that can be converted to NumPy.
            trace_kwargs (dict or list of dict, optional): Keyword arguments passed to each [`plotly.graph_objects.Bar`](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Bar.html).
            **layout_kwargs: Keyword arguments for layout.
        Examples:
            One trace:
            ```py
            vbt.Bar(['x', 'y'], trace_names='a', data=[1, 2])
            ```
            ![](img/Bar.png)

            Multiple traces:
            ```py
            vbt.Bar(['x', 'y'], trace_names=['a', 'b'], data=[[1, 2], [3, 4]])
            ```
            ![](img/Bar_mult.png)
            """
        if isinstance(trace_names, str) or trace_names is None:
            trace_names = [trace_names]
        self._x_labels = x_labels
        self._trace_names = trace_names

        super().__init__()
        if len(trace_names) > 1 or trace_names[0] is not None:
            self.update_layout(showlegend=True)
        self.update_layout(**layout_kwargs)

        # Add traces
        for i, trace_name in enumerate(trace_names):
            bar = go.Bar(
                x=x_labels,
                name=trace_name
            )
            bar.update(**(trace_kwargs[i] if isinstance(trace_kwargs, (list, tuple)) else trace_kwargs))
            self.add_trace(bar)

        if data is not None:
            self.update_data(data)

    def update_data(self, data):
        """Update the data of the plot efficiently.

        Args:
            data (array_like): Data in any format that can be converted to NumPy.

                Must be of shape (`x_labels`, `trace_names`).
        Examples:
            ```py
            fig = pd.Series([1, 2], index=['x', 'y'], name='a').vbt.Bar()
            fig.update_data([2, 1])
            fig.show()
            ```
            ![](img/Bar_updated.png)
        """
        if not checks.is_array(data):
            data = np.asarray(data)
        data = reshape_fns.to_2d(data)
        checks.assert_same_shape(data, self._x_labels, along_axis=(0, 0))
        checks.assert_same_shape(data, self._trace_names, along_axis=(1, 0))

        # Update traces
        with self.batch_update():
            for i, bar in enumerate(self.data):
                bar.y = data[:, i]
                if bar.marker.colorscale is not None:
                    bar.marker.color = data[:, i]


# ############# Scatter ############# #


class Scatter(UpdatableFigureWidget):
    def __init__(self, x_labels, trace_names=None, data=None, trace_kwargs={}, **layout_kwargs):
        """Create an updatable scatter plot.

        Args:
            x_labels (list of str): X-axis labels, corresponding to index in pandas.
            trace_names (str or list of str, optional): Trace names, corresponding to columns in pandas.
            data (array_like, optional): Data in any format that can be converted to NumPy.
            trace_kwargs (dict or list of dict, optional): Keyword arguments passed to each [`plotly.graph_objects.Scatter`](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatter.html).
            **layout_kwargs: Keyword arguments for layout.
        Examples:
            ```py
            vbt.Scatter(['x', 'y'], trace_names=['a', 'b'], data=[[1, 2], [3, 4]])
            ```
            ![](img/Scatter.png)
            """

        if isinstance(trace_names, str) or trace_names is None:
            trace_names = [trace_names]
        self._x_labels = x_labels
        self._trace_names = trace_names

        super().__init__()
        if len(trace_names) > 1 or trace_names[0] is not None:
            self.update_layout(showlegend=True)
        self.update_layout(**layout_kwargs)

        # Add traces
        for i, trace_name in enumerate(trace_names):
            scatter = go.Scatter(
                x=x_labels,
                name=trace_name
            )
            scatter.update(**(trace_kwargs[i] if isinstance(trace_kwargs, (list, tuple)) else trace_kwargs))
            self.add_trace(scatter)

        if data is not None:
            self.update_data(data)

    def update_data(self, data):
        """Update the data of the plot efficiently.

        Args:
            data (array_like): Data in any format that can be converted to NumPy.

                Must be of shape (`x_labels`, `trace_names`).
        """
        if not checks.is_array(data):
            data = np.asarray(data)
        data = reshape_fns.to_2d(data)
        checks.assert_same_shape(data, self._x_labels, along_axis=(0, 0))
        checks.assert_same_shape(data, self._trace_names, along_axis=(1, 0))

        # Update traces
        with self.batch_update():
            for i, scatter in enumerate(self.data):
                scatter.y = data[:, i]


# ############# Histogram ############# #


class Histogram(UpdatableFigureWidget):
    def __init__(self, trace_names=None, data=None, horizontal=False, trace_kwargs={}, **layout_kwargs):
        """Create an updatable histogram plot.

        Args:
            trace_names (str or list of str, optional): Trace names, corresponding to columns in pandas.
            data (array_like, optional): Data in any format that can be converted to NumPy.
            horizontal (bool): Plot horizontally. Defaults to False.
            trace_kwargs (dict or list of dict, optional): Keyword arguments passed to each [`plotly.graph_objects.Histogram`](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Histogram.html)
            **layout_kwargs: Keyword arguments for layout
        Examples:
            ```py
            vbt.Histogram(trace_names=['a', 'b'], data=[[1, 2], [3, 4], [2, 1]])
            ```
            ![](img/Histogram.png)
            """

        if isinstance(trace_names, str) or trace_names is None:
            trace_names = [trace_names]
        self._trace_names = trace_names
        self._horizontal = horizontal

        super().__init__()
        if len(trace_names) > 1 or trace_names[0] is not None:
            self.update_layout(showlegend=True)
        self.update_layout(barmode='overlay')
        self.update_layout(**layout_kwargs)

        # Add traces
        for i, trace_name in enumerate(trace_names):
            histogram = go.Histogram(
                name=trace_name,
                opacity=0.75 if len(trace_names) > 1 else 1
            )
            histogram.update(**(trace_kwargs[i] if isinstance(trace_kwargs, (list, tuple)) else trace_kwargs))
            self.add_trace(histogram)

        if data is not None:
            self.update_data(data)

    def update_data(self, data):
        """Update the data of the plot efficiently.

        Args:
            data (array_like): Data in any format that can be converted to NumPy.

                Must be of shape (any, `trace_names`).
        """
        if not checks.is_array(data):
            data = np.asarray(data)
        data = reshape_fns.to_2d(data)
        checks.assert_same_shape(data, self._trace_names, along_axis=(1, 0))

        # Update traces
        with self.batch_update():
            for i, histogram in enumerate(self.data):
                if self._horizontal:
                    histogram.x = None
                    histogram.y = data[:, i]
                else:
                    histogram.x = data[:, i]
                    histogram.y = None



# ############# Heatmap ############# #

class Heatmap(UpdatableFigureWidget):
    def __init__(self, x_labels, y_labels, data=None, horizontal=False, trace_kwargs={}, **layout_kwargs):
        """Create an updatable heatmap plot.

        Args:
            x_labels (list of str): X-axis labels, corresponding to columns in pandas.
            y_labels (list of str): Y-axis labels, corresponding to index in pandas.
            data (array_like, optional): Data in any format that can be converted to NumPy.
            horizontal (bool): Plot horizontally. Defaults to False.
            trace_kwargs (dict or list of dict, optional): Keyword arguments passed to each [`plotly.graph_objects.Heatmap`](https://plotly.com/python-api-reference/generated/plotly.graph_objects.Heatmap.html).
            **layout_kwargs: Keyword arguments for layout.
        Examples:
            ```py
            vbt.Heatmap(['a', 'b'], ['x', 'y'], data=[[1, 2], [3, 4]])
            ```
            ![](img/Heatmap.png)
            """

        self._x_labels = x_labels
        self._y_labels = y_labels
        self._horizontal = horizontal

        super().__init__()
        self.update_layout(**layout_kwargs)

        # Add traces
        heatmap = go.Heatmap(
            hoverongaps=False,
            colorscale='Plasma'
        )
        if self._horizontal:
            heatmap.y = x_labels
            heatmap.x = y_labels
        else:
            heatmap.x = x_labels
            heatmap.y = y_labels
        heatmap.update(**trace_kwargs)
        self.add_trace(heatmap)

        if data is not None:
            self.update_data(data)

    def update_data(self, data):
        """Update the data of the plot efficiently.

        Args:
            data (array_like): Data in any format that can be converted to NumPy.

                Must be of shape (`y_labels`, `x_labels`).
        """
        if not checks.is_array(data):
            data = np.asarray(data)
        data = reshape_fns.to_2d(data)
        checks.assert_same_shape(data, self._x_labels, along_axis=(1, 0))
        checks.assert_same_shape(data, self._y_labels, along_axis=(0, 0))

        # Update traces
        with self.batch_update():
            heatmap = self.data[0]
            if self._horizontal:
                heatmap.z = data.transpose()
            else:
                heatmap.z = data


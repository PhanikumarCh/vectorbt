import numpy as np
import pandas as pd

from vectorbt.utils import checks


def from_values(values, name=None, value_names=None):
    """Create index using array of values."""
    if value_names is not None:
        checks.assert_same_shape(values, value_names, along_axis=0)
        return pd.Index(value_names, name=name)  # just return the names
    value_names = []
    for i, v in enumerate(values):
        if not checks.is_array(v):
            v = np.asarray(v)
        if np.all(v == v.item(0)):
            value_names.append(v.item(0))
        else:
            value_names.append('mix_%d' % i)
    return pd.Index(value_names, name=name)


def repeat(index, n):
    """Repeat each element in index n times."""
    if not isinstance(index, pd.Index):
        index = pd.Index(index)

    return np.repeat(index, n)


def tile(index, n):
    """Tile the whole index n times."""
    if not isinstance(index, pd.Index):
        index = pd.Index(index)

    if isinstance(index, pd.MultiIndex):
        return pd.MultiIndex.from_tuples(np.tile(index, n), names=index.names)
    return pd.Index(np.tile(index, n), name=index.name)


def stack(*indexes):
    """Stack indexes."""
    new_index = indexes[0]
    for i in range(1, len(indexes)):
        index1, index2 = new_index, indexes[i]
        checks.assert_same_shape(index1, index2)
        if not isinstance(index1, pd.MultiIndex):
            index1 = pd.MultiIndex.from_arrays([index1])
        if not isinstance(index2, pd.MultiIndex):
            index2 = pd.MultiIndex.from_arrays([index2])

        levels = []
        for i in range(len(index1.names)):
            levels.append(index1.get_level_values(i))
        for i in range(len(index2.names)):
            levels.append(index2.get_level_values(i))

        new_index = pd.MultiIndex.from_arrays(levels)
    return new_index


def combine(*indexes):
    """Combine indexes using Cartesian product."""
    new_index = indexes[0]
    for i in range(1, len(indexes)):
        index1, index2 = new_index, indexes[i]
        if not isinstance(index1, pd.Index):
            index1 = pd.Index(index1)
        if not isinstance(index2, pd.Index):
            index2 = pd.Index(index2)

        if len(index1) == 1:
            return index2
        elif len(index2) == 1:
            return index1

        tuples1 = np.repeat(index1.to_numpy(), len(index2))
        tuples2 = np.tile(index2.to_numpy(), len(index1))

        if isinstance(index1, pd.MultiIndex):
            index1 = pd.MultiIndex.from_tuples(tuples1, names=index1.names)
        else:
            index1 = pd.Index(tuples1, name=index1.name)
        if isinstance(index2, pd.MultiIndex):
            index2 = pd.MultiIndex.from_tuples(tuples2, names=index2.names)
        else:
            index2 = pd.Index(tuples2, name=index2.name)

        new_index = stack(index1, index2)
    return new_index


def drop_levels(index, levels):
    """Drop levels from index."""
    checks.assert_type(index, pd.MultiIndex)

    levels_to_drop = []
    if not isinstance(levels, (tuple, list)):
        levels = [levels]
    for level in levels:
        if level in index.names:
            levels_to_drop.append(level)
    if len(levels_to_drop) < len(index.names):
        # Drop only if there will be some indexes left
        return index.droplevel(levels_to_drop)
    return index


def rename_levels(index, name_dict):
    """Rename index/column levels."""
    for k, v in name_dict.items():
        if isinstance(index, pd.MultiIndex):
            if k in index.names:
                index = index.rename(v, level=k)
        else:
            if index.name == k:
                index.name = v
    return index


def select_levels(index, level_names):
    """Build a new index by selecting one or multiple level names from the index."""
    checks.assert_type(index, pd.MultiIndex)

    if isinstance(level_names, (list, tuple)):
        levels = [index.get_level_values(level_name) for level_name in level_names]
        return pd.MultiIndex.from_arrays(levels)
    else:
        return index.get_level_values(level_names)


def drop_redundant_levels(index):
    """Drop levels that have a single value."""
    if not isinstance(index, pd.Index):
        index = pd.Index(index)
    if len(index) == 1:
        return index

    if isinstance(index, pd.MultiIndex):
        levels_to_drop = []
        for i, level in enumerate(index.levels):
            if len(level) == 1:
                levels_to_drop.append(i)
            elif level.name is None and (level == np.arange(len(level))).all():  # basic range
                if len(index.get_level_values(i)) == len(level):
                    levels_to_drop.append(i)
        # Remove redundant levels only if there are some non-redundant levels left
        if len(levels_to_drop) < len(index.levels):
            return index.droplevel(levels_to_drop)
    return index


def drop_duplicate_levels(index, keep='last'):
    """Drop duplicate levels with the same name and values."""
    if isinstance(index, pd.Index) and not isinstance(index, pd.MultiIndex):
        return index
    checks.assert_type(index, pd.MultiIndex)

    levels = []
    levels_to_drop = []
    if keep == 'first':
        r = range(0, len(index.levels))
    elif keep == 'last':
        r = range(len(index.levels)-1, -1, -1)  # loop backwards
    for i in r:
        level = (index.levels[i].name, tuple(index.get_level_values(i).to_numpy().tolist()))
        if level not in levels:
            levels.append(level)
        else:
            levels_to_drop.append(i)
    return index.droplevel(levels_to_drop)


def align_to(index1, index2):
    """Align the first index to the second one. 

    Returns integer indexes of occurrences and None if aligning not needed.

    The second one must contain all levels from the first (and can have some more)
    In all these levels, both must share the same elements.
    Only then the first index can be broadcasted to the match the shape of the second one."""
    if not isinstance(index1, pd.MultiIndex):
        index1 = pd.MultiIndex.from_arrays([index1])
    if not isinstance(index2, pd.MultiIndex):
        index2 = pd.MultiIndex.from_arrays([index2])
    if index1.duplicated().any():
        raise ValueError("Duplicates index values are not allowed for the first index")

    if pd.Index.equals(index1, index2):
        return pd.IndexSlice[:]
    if len(index1) <= len(index2):
        if len(index1) == 1:
            return pd.IndexSlice[np.tile([0])]
        js = []
        for i in range(len(index1.names)):
            for j in range(len(index2.names)):
                if index1.names[i] == index2.names[j]:
                    if np.array_equal(index1.levels[i], index2.levels[j]):
                        js.append(j)
                        break
        if len(index1.names) == len(js):
            new_index = pd.MultiIndex.from_arrays([index2.get_level_values(j) for j in js])
            xsorted = np.argsort(index1)
            ypos = np.searchsorted(index1[xsorted], new_index)
            return pd.IndexSlice[xsorted[ypos]]

    raise ValueError("Indexes could not be aligned together")
#  -*- coding: utf-8 -*-
"""Helper functions for limp.

@author: Stefan Peterson
"""

from ._classes import Dependency

try:
    from math import inf
except ImportError:     # For Python 2
    inf = float('inf')


def is_iterable(x):
    """Check if a variable is a non-string iterable.

    Parameters
    ----------
    x : Any

    Returns
    -------
    bool
    """

    return isinstance(x, (tuple, list, set)) and not isinstance(x, Dependency)


def recursive_map(f, x):
    """A map that recursively descends tuples, lists, sets and dicts.

    Parameters
    ----------
    f : Callable
    x : Any

    Returns
    -------
    Any
    """

    if isinstance(x, dict):
        return {key: recursive_map(f, val) for key, val in x.iteritems()}
    elif is_iterable(x):
        return type(x)(map(lambda y: recursive_map(f, y), x))
    else:
        return f(x)


def list_dependencies(args):
    """List dependencies in arguments.

    Parameters
    ----------
    args : Any
        A single argument, an iterable of arguments or a dict of keyword
        arguments

    Returns
    -------
    List[Hashable]
        A list of dependencies
    """

    dependencies = []

    if isinstance(args, Dependency):
        return[args.task_id]
    elif isinstance(args, dict):
        iterable_args = args.values()
    elif is_iterable(args):
        iterable_args = args
    else:
        return []

    for val in iterable_args:
        if isinstance(val, dict) or is_iterable(val):
            dependencies.extend(list_dependencies(val))
        elif isinstance(val, Dependency):
            dependencies.append(val.task_id)

    return list(set(dependencies))


def successor_graph(graph):
    """Generate a graph showing the successor tasks for each task.

    Parameters
    ----------
    graph : Dict[Hashable, (Callable, Any, Number)]
        A directed acyclic graph representing the computations where each
        vertex represents a computational task

    Returns
    -------
    Dict[Hashable, List[Hashable]]
        A simplified graph including showing only successor tasks for each task
    """

    return {key: [key_ for (key_, val_) in graph.items()
                  if key in list_dependencies(val_[1])]
            for (key, val) in graph.items()}


def reverse_graph(graph):
    """Reverse a directed graph.

    Parameters
    ----------
    graph : Dict[Hashable, List[Hashable]]
        A graph on the form {node: [successor]}

    Returns
    -------
    Dict[Hashable, List[Hashable]]
        A graph with all directions reversed
    """
    graph_ = {vertex: [] for vertex in graph}
    for vertex, successors in graph.items():
        for vertex_ in successors:
            graph_[vertex_].append(vertex)

    return graph_


def to_dot(graph, fill_color="lightblue"):
    """Generate a description of a graph in graphviz's DOT language.

    Parameters
    ----------
    graph : Dict[Hashable, (Callable, Any, Number)]
        A directed acyclic graph representing the computations where each
        vertex represents a computational task. The graph is represented by a
        dict with task IDs as keys and tuples of (function, arguments,
        computational cost) as values. Edges are implied by ``Dependency``
        instances among arguments.
    fill_color : Optional[str]
        Node fill color, default is 'lightblue'.

    Returns
    -------
    str
    """

    dot_template = """digraph G {{
    {{
        node [style=filled]
        {}
    }}
    {}
}}"""

    sg = successor_graph(graph)
    preamble = "\n        ".join(map(
        lambda x: dot_node_string(x) + " [fillcolor={}]".format(fill_color),
        sg.iterkeys()))
    body = "\n    ".join("{} -> {};".format(dot_node_string(v),
                                            ", ".join(map(dot_node_string,
                                                          ws)))
                         for v, ws in sg.iteritems() if len(ws) > 0)

    return dot_template.format(preamble, body)


def dot_node_string(task_id):
    """Format any task ID as a quoted string.

    Parameters
    ----------
    task_id : Hashable

    Returns
    -------
    str
    """
    if isinstance(task_id, tuple):
        return "\"" + ", ".join(map(str, task_id)) + "\""
    else:
        return "\"" + str(task_id) + "\""


def equivalent_args(args_0, args_1):
    """Compare args in a way that handles problematic types such as numpy
    arrays.

    Parameters
    ----------
    args_0 : Any
    args_1 : Any

    Returns
    -------
    bool
    """

    if isinstance(args_0, dict):
        if isinstance(args_1, dict):
            for key in args_0:
                if key not in args_1:
                    return False
                elif equivalent_args(args_0[key], args_1[key]) is False:
                    return False
            for key in args_1:
                if key not in args_0:
                    return False
        else:
            return False

    elif is_iterable(args_0):
        if is_iterable(args_1):
            try:
                return (args_0 == args_1) is True
            except ValueError:
                return all(equivalent_args(a, b)
                           for a, b in zip(args_0, args_1))
        else:
            return False

    else:
        return (args_0 == args_1) is True

    return True


def demux(xs):
    """De-multiplex an iterable of tuples by their first value.

    Parameters
    ----------
    xs: Iterable[Tuple[Hashable, Hashable]]

    Returns
    -------
    List[Hashable]
    """

    demux_dict = {}
    for x in xs:
        if x[0] in demux_dict:
            demux_dict[x[0]].append(x[1])
        else:
            demux_dict[x[0]] = [x[1]]

    return list(demux_dict.items())

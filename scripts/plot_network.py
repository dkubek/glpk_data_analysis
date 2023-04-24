import sys
import json
import argparse

import networkx as nx
import matplotlib.pyplot as plt

from construct_mmcf_problem import Network

from pathlib import Path


def custom_layout(G, source_vertices, target_vertices):
    pos_kamada_kawai = nx.kamada_kawai_layout(G)

    x_min = min(pos_kamada_kawai.values(), key=lambda x: x[0])[0]
    x_max = max(pos_kamada_kawai.values(), key=lambda x: x[0])[0]

    pos_custom = {}
    y_target = 0.1
    y_source = 0.1
    target_delta = 0.3
    source_delta = 0.3

    for node in G:
        if node in target_vertices:
            pos_custom[node] = (x_max + 0.2, y_target)
            y_target += target_delta
        elif node in source_vertices:
            pos_custom[node] = (x_min - 0.2, y_source)
            y_source += source_delta
        else:
            pos_custom[node] = pos_kamada_kawai[node]

    return pos_custom


def visualize_directed_graph(network: Network):
    G = nx.DiGraph()

    source_vertices = [_['id'] for _ in network.sources.values()]
    target_vertices = [_['id'] for _ in network.targets.values()]

    for vertex in network.graph:
        out_vertices = network.graph[vertex]["out"]
        G.add_node(vertex)
        for out_vertex in out_vertices:
            G.add_edge(vertex, out_vertex)

    pos = custom_layout(G, source_vertices, target_vertices)
    #pos = nx.kamada_kawai_layout(G)

    default_nodes = set(G.nodes) - set(source_vertices) - set(target_vertices)
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=default_nodes,
        node_color='gray',
    )
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=source_vertices,
        node_color='green',
    )
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=target_vertices,
        node_color='red',
    )

    # Draw incoming and outgoing edges with different colors
    incoming_edges = [(u, v) for u, v in G.edges if v in target_vertices]
    outgoing_edges = [(u, v) for u, v in G.edges if u in source_vertices]

    bad_edges = [(u, v) for u, v in G.edges
                 if (u not in source_vertices and v in source_vertices) or (
                     u in target_vertices and v not in target_vertices)]
    special = set(incoming_edges + outgoing_edges + bad_edges)
    rest = [e for e in G.edges if e not in special]

    nx.draw_networkx_edges(G,
                           pos,
                           edgelist=incoming_edges,
                           edge_color='blue',
                           connectionstyle='arc3,rad=0.1')
    nx.draw_networkx_edges(G,
                           pos,
                           edgelist=outgoing_edges,
                           edge_color='orange',
                           connectionstyle='arc3,rad=0.1')
    nx.draw_networkx_edges(G,
                           pos,
                           edgelist=bad_edges,
                           edge_color='red',
                           connectionstyle='arc3,rad=0.1')
    nx.draw_networkx_edges(G, pos, edgelist=rest, edge_color='black')

    labels = {v: v for v in source_vertices + target_vertices}
    nx.draw_networkx_labels(G, pos, labels=labels)

    plt.axis("off")
    plt.savefig("fig.pdf")


def main(input_filename, output_filename):
    contents = None
    with open(input_filename, 'r') as fin:
        contents = json.load(fin)

    network = Network(contents)
    visualize_directed_graph(network)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("input_file", type=Path, help="MMCF instance in JSON")
    parser.add_argument("-o",
                        "--output_file",
                        required=False,
                        default=None,
                        type=Path,
                        help="Output file of the resulting LP")

    args = parser.parse_args(sys.argv[1:])

    output_file = (args.input_file.stem +
                   '.lp' if args.output_file is None else args.output_file)
    main(args.input_file, output_file)

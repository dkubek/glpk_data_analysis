import sys
import json
import pulp
import argparse

from pathlib import Path


def is_supply_node(demands, vertex, commodity):
    vertex = str(vertex)
    commodity = str(commodity)

    return demands[vertex].get(commodity, 0) < 0


def is_target_node(demands, vertex, commodity):
    vertex = str(vertex)
    commodity = str(commodity)

    return demands[vertex].get(commodity, 0) > 0


def build_graph(arcs):
    graph = {}
    for arc in arcs:
        u, v = arc['from'], arc['to']

        u_data = graph.setdefault(u, {})
        out_nodes = u_data.setdefault("out", set())
        out_nodes.add(v)

        v_data = graph.setdefault(v, {})
        in_nodes = v_data.setdefault("in", set())
        in_nodes.add(u)

    return graph


def build_model(contents, name="(unknown)", demand_scale=1):
    model = pulp.LpProblem(name=name, sense=pulp.LpMinimize)

    info = contents['info']
    arcs = contents['arcs']
    demands = contents['demands']

    graph = build_graph(arcs)
    commodities = range(1, info['no_commodities'] + 1)

    # Initialize flow and violation variables
    variables = {"flow": {}, "violation": {}}
    for arc in arcs:
        u, v = arc['from'], arc['to']
        variables["violation"][(u, v)] = pulp.LpVariable(
            name="v_({}-{})".format(u, v), lowBound=0)

        for commodity in commodities:
            variables["flow"][(u, v, commodity)] = pulp.LpVariable(
                name="f_({}-{})@{}".format(u, v, commodity), lowBound=0
            )

    # Objective function
    model += pulp.lpSum(
        [
            variables["violation"][(arc['from'], arc['to'])]
            for arc in arcs
        ]
    )

    # Edge capacities
    for arc in arcs:
        u, v, capacity = arc['from'], arc['to'], arc['capacity']

        model += (
            pulp.lpSum(
                [
                    variables["flow"][(u, v, commodity)]
                    for commodity in commodities
                ]
            )
            - variables["violation"][(u, v)]
            <= capacity
        )

    # Kirchhof
    for commodity in commodities:
        for vertex in graph:
            is_special = (is_supply_node(demands, vertex, commodity)
                          or is_target_node(demands, vertex, commodity))

            if is_special:
                continue

            outgoing = pulp.lpSum(
                [
                    variables["flow"][(vertex, v, commodity)]
                    for v in graph[vertex].get("out", {})
                ]
            )

            incomming = pulp.lpSum(
                [
                    variables["flow"][(u, vertex, commodity)]
                    for u in graph[vertex].get("in", {})
                ]
            )

            model += outgoing - incomming == 0

    for vertex in graph:
        for commodity in commodities:
            if not is_target_node(demands, vertex, commodity):
                continue

            incomming = pulp.lpSum(
                [
                    variables["flow"][(u, vertex, commodity)]
                    for u in graph[vertex].get("in", [])
                ]
            )
            model += incomming >= demand_scale * \
                demands[str(vertex)][str(commodity)]

    for vertex in graph:
        for commodity in commodities:
            if not is_supply_node(demands, vertex, commodity):
                continue

            outgoing = pulp.lpSum(
                [
                    variables["flow"][(vertex, u, commodity)]
                    for u in graph[vertex].get("out", [])
                ]
            )
            model += outgoing <= -demands[str(vertex)][str(commodity)]

    return model, variables


def main(input_filename, output_filename):
    contents = None
    with open(input_filename, 'r') as fin:
        contents = json.load(fin)

    model, variables = build_model(contents)
    model.writeLP(output_filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("input_file", type=Path, help="MMCF instance in JSON")
    parser.add_argument("-o", "--output_file", required=False, default=None,
                        type=Path, help="Output file of the resulting MPS")

    args = parser.parse_args(sys.argv[1:])

    output_file = (args.input_file.stem + '.lp' if args.output_file is None else args.output_file)
    main(args.input_file, output_file)

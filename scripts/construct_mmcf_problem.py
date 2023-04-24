import sys
import json
import pulp
import argparse

from pathlib import Path


def build_graph(arcs):
    graph = {}
    for _, arc in arcs:
        u, v = arc['from'], arc['to']

        u_data = graph.setdefault(u, {"out": set(), "in": set()})
        u_data["out"].add(v)

        v_data = graph.setdefault(v, {"out": set(), "in": set()})
        v_data["in"].add(u)

    return graph


class CommodityCost:

    def __init__(self, arcs):
        self._data = dict()
        for id, arc in arcs:
            self._data[id] = arc['cost']

    def __getitem__(self, key):
        id, commodity = tuple(map(int, key))

        cost = self._data.get(id)

        if cost is None:
            return None

        if type(cost) is dict:
            return cost[commodity]

        return cost


class Network:

    def __init__(self, contents):
        info = contents['info']
        self.no_nodes = int(info['no_nodes'])
        self.no_arcs = int(info['no_arcs'])
        self.no_commodities = int(info['no_commodities'])
        self.commodities = range(self.no_commodities)

        self.arcs = contents['arcs']

        # Make single sourced/target
        demands = contents['demands']
        self.sources = {}
        self.targets = {}
        for vertex in demands:
            for commodity in demands[vertex]:
                demand = demands[vertex][commodity]
                if demand == 0:
                    continue

                commodity = int(commodity)
                v = int(vertex)

                new_arc = {'cost': 0}
                # vertex is a target
                if demand > 0:
                    if commodity not in self.targets:
                        self.targets[commodity] = {
                            'id': self.no_nodes,
                            'demand': 0
                        }
                        self.no_nodes += 1

                    node_id = self.targets[commodity]['id']
                    new_arc['from'] = v
                    new_arc['to'] = node_id
                    new_arc['capacity'] = abs(demand)

                    self.targets[commodity]['demand'] += demand

                # vertex is a source
                if demand < 0:
                    if commodity not in self.sources:
                        self.sources[commodity] = {
                            'id': self.no_nodes,
                            'demand': 0
                        }
                        self.no_nodes += 1

                    node_id = self.sources[commodity]['id']
                    new_arc['from'] = node_id
                    new_arc['to'] = v
                    new_arc['capacity'] = abs(demand)

                    self.sources[commodity]['demand'] += demand

                self.arcs.append(new_arc)
                self.no_arcs += 1

        self.arcs = list(enumerate(self.arcs))

        for commodity in self.commodities:
            d = min(abs(self.sources[commodity]['demand']),
                    abs(self.targets[commodity]['demand']))

            self.sources[commodity]['demand'] = -d
            self.targets[commodity]['demand'] = d

        self.graph = build_graph(self.arcs)
        print(self.graph)
        print(self.sources)
        print(self.targets)

        self.costs = CommodityCost(self.arcs)

        self.valid_arcs = set()
        for id, arc in self.arcs:
            u, v = arc['from'], arc['to']

            for commodity in self.commodities:
                commodity_cost = self.costs[(id, commodity)]
                if commodity_cost is not None:
                    self.valid_arcs.add((id, u, v, commodity))

    def is_source_node(self, vertex, commodity):
        vertex, commodity = int(vertex), int(commodity)
        return vertex == self.sources[commodity]['id']

    def is_target_node(self, vertex, commodity):
        vertex, commodity = int(vertex), int(commodity)
        return vertex == self.targets[commodity]['id']

    def get_demand(self, vertex, commodity):
        vertex, commodity = int(vertex), int(commodity)

        if self.is_target_node(vertex, commodity):
            return self.targets[commodity]['demand']

        if self.is_source_node(vertex, commodity):
            return self.sources[commodity]['demand']

        return 0


def build_model_mmcf(network, name="(unknown)", demand_scale=1):
    model = pulp.LpProblem(name=name, sense=pulp.LpMinimize)

    variables = {}
    for id, u, v, commodity in network.valid_arcs:
        uv_flows = variables.setdefault((u, v), dict())
        uv_flows[(id, commodity)] = (pulp.LpVariable(
            name="f{}_({}-{})@{}".format(id, u, v, commodity), lowBound=0))

    # Objective function
    model += pulp.lpSum([
        network.costs[(id, commodity)] * variables[(u, v)][(id, commodity)]
        for id, u, v, commodity in network.valid_arcs
        if network.costs[(id, commodity)] != 0
    ])

    # Edge capacities
    for id, arc in network.arcs:
        u, v, capacity = arc['from'], arc['to'], arc['capacity']

        assert capacity >= 0
        model += (pulp.lpSum([
            variables[(u, v)][(id, commodity)]
            for commodity in network.commodities
            if (id, u, v, commodity) in network.valid_arcs
        ]) <= capacity, f"CAP[{id}]{u}_{v}")

    # Kirchhof
    for vertex in network.graph:
        for commodity in network.commodities:
            outgoing = pulp.lpSum([
                variables[(vertex, v)][(id, commodity)]
                for v in network.graph[vertex].get("out", {})
                for id, c in variables[(vertex, v)]
                if c == commodity
                if (id, vertex, v, commodity) in network.valid_arcs
            ])

            incomming = pulp.lpSum([
                variables[(u, vertex)][(id, commodity)]
                for u in network.graph[vertex].get("in", {})
                for id, c in variables[(u, vertex)]
                if c == commodity
                if (id, u, vertex, commodity) in network.valid_arcs
            ])

            demand = network.get_demand(vertex, commodity)
            if network.is_source_node(vertex, commodity):
                if demand == 0:
                    continue

            if network.is_target_node(vertex, commodity):
                if demand == 0:
                    continue

            model += (incomming - outgoing == demand, f"KIR_{vertex}_{commodity}")

    return model, variables


def build_model_network(network: Network):
    lines = []

    lines.append(str(network.no_nodes))
    for i in range(network.no_nodes):
        lines.append(f"{i} 0 0")

    lines.append(str(network.no_arcs))
    for i, arc in enumerate(network.arcs):
        src, dest, capacity, cost = (arc["from"], arc["to"], arc["capacity"],
                                     arc["cost"])
        if type(cost) == dict:
            sys.stderr.write("Not unified costs. Aborting.")
            sys.exit(1)

        lines.append(f"{i} {src} {dest} {capacity} {cost}")

    lines.append(str(network.no_commodities))
    for commodity in network.commodities:
        src = network.sources[commodity]['id']
        dest = network.targets[commodity]['id']
        amount = network.targets[commodity]['demand']

        lines.append(f"{commodity} {src} {dest} {amount}")

    return '\n'.join(lines)


def main(args):
    input_filename = args.input_file
    output_filename = (args.input_file.stem + '.' + args.type
                       if args.output_file is None else args.output_file)

    contents = None
    with open(input_filename, 'r') as fin:
        contents = json.load(fin)

    network = Network(contents)

    if args.type == 'lp':
        model, _ = build_model_mmcf(network)
        #solver = pulp.getSolver('GLPK_CMD')
        #model.solve(solver)

        model.writeLP(output_filename)
    elif args.type == 'network':
        model = build_model_network(network)
        with open(output_filename, 'w') as fout:
            fout.writelines(model)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("input_file", type=Path, help="MMCF instance in JSON")
    parser.add_argument("-o",
                        "--output_file",
                        required=False,
                        default=None,
                        type=Path,
                        help="Output file of the resulting LP")
    parser.add_argument(
        "-t",
        "--type",
        choices=["network", "lp"],
        default="lp",
        help="Choose between 'network' and 'lp' modes. Default is 'lp'.")

    args = parser.parse_args(sys.argv[1:])

    main(args)

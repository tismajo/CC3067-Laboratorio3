import argparse
import json
from pathlib import Path

from node.algorithms.dijkstra.dijkstra import DijkstraRoutingAlgorithm
from node.algorithms.dijkstra.topology import Topology
from node.algorithms.flooding.flooding import FloodingRoutingAlgorithm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=["dijkstra", "flooding", "lsr"],
    )
    args = parser.parse_args()

    if args.mode == "lsr":
        parser.error(f"el modo {args.mode} todavía no está implementado")

    config = json.loads(
        Path(args.config).read_text(encoding="utf-8")
    )
    if args.mode == "flooding":
        algorithm = FloodingRoutingAlgorithm(self_info=config)
        algorithm.initialize(config["node_id"], config["neighbors"])

        print(f"Flooding desde {config['node_id']}")
        print(
            "vecinos configurados: "
            + ", ".join(
                neighbor["node_id"]
                for neighbor in algorithm.neighbor_table.get_neighbors()
            )
        )
        print(f"HELLO pendientes: {len(algorithm.get_outgoing_packets())}")
        return

    algorithm = DijkstraRoutingAlgorithm(Topology.from_json(config))
    algorithm.initialize(config["node_id"], config["neighbors"])

    print(f"Rutas desde {config['node_id']}")
    print("destino\tcosto\tsiguiente salto")
    for destination in sorted(algorithm.paths):
        if destination == config["node_id"]:
            continue
        cost, next_hop = algorithm.paths[destination]
        print(f"{destination}\t{cost:g}\t{next_hop or '-'}")


if __name__ == "__main__":
    main()

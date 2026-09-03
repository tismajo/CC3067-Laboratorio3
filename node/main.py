import argparse
import json
import sys
import time
from pathlib import Path

from node.algorithms.dijkstra.dijkstra import DijkstraRoutingAlgorithm
from node.algorithms.dijkstra.topology import Topology
from node.algorithms.flooding.flooding import FloodingRoutingAlgorithm
from node.algorithms.lsr.link_state import LinkStateRouter
from node.network.forwarding import Forwarder
from node.network.health_check import HealthChecker
from node.network.socket_manager import SocketManager
from node.routing.routing_table import RoutingTable
from shared import constants as c
from shared.protocol import build_packet


def _build_algorithm(mode: str, config: dict):
    if mode == "flooding":
        algorithm = FloodingRoutingAlgorithm(self_info=config)
    elif mode == "lsr":
        algorithm = LinkStateRouter(self_info=config)
    else:
        algorithm = DijkstraRoutingAlgorithm(Topology.from_json(config))
    algorithm.initialize(config["node_id"], config["neighbors"])
    return algorithm


def _print_standalone_summary(mode: str, config: dict, algorithm) -> None:
    if mode == "flooding":
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

    if mode == "lsr":
        own_lsp = algorithm.lsp_db.get(config["node_id"], {})
        print(f"LSP de {config['node_id']} (seq {own_lsp.get('sequence')})")
        for link in own_lsp.get("neighbors", []):
            print(f"{link['node_id']}\t{link['weight']:g}")
        print(f"Rutas desde {config['node_id']}")
        print("destino\tsiguiente salto")
        for destination in sorted(algorithm.routing_table):
            print(f"{destination}\t{algorithm.routing_table[destination]}")
        return

    print(f"Rutas desde {config['node_id']}")
    print("destino\tcosto\tsiguiente salto")
    for destination in sorted(algorithm.paths):
        if destination == config["node_id"]:
            continue
        cost, next_hop = algorithm.paths[destination]
        print(f"{destination}\t{cost:g}\t{next_hop or '-'}")


def _run_live(mode: str, config: dict, algorithm) -> None:
    node_id = config["node_id"]
    neighbor_addresses = {
        neighbor["node_id"]: {"ip": neighbor["ip"], "port": neighbor["port"]}
        for neighbor in config["neighbors"]
    }

    routing_table = RoutingTable()
    socket_manager = SocketManager(config["ip"], config["port"])
    forwarder = Forwarder(
        node_id=node_id,
        proto=mode,
        algorithm=algorithm,
        routing_table=routing_table,
        socket_manager=socket_manager,
        neighbor_addresses=neighbor_addresses,
    )

    def on_packet_received(raw, addr):
        try:
            forwarder.handle_incoming_packet(raw, addr)
        except (ValueError, KeyError) as error:
            print(f"[{node_id}] paquete inválido descartado: {error}")

    def send_ping(neighbor):
        packet = build_packet(
            proto=mode,
            type_=c.TYPE_HELLO,
            from_=node_id,
            to=neighbor["node_id"],
            ttl=1,
            payload={
                "node_id": node_id,
                "ip": config["ip"],
                "port": config["port"],
                # sent_at deja que el receptor calcule el retardo del enlace
                # (NeighborTable.on_hello_received).
                "sent_at": time.time(),
            },
        )
        socket_manager.send(neighbor["ip"], neighbor["port"], packet)

    def on_status_change(neighbor_id, is_up):
        if is_up:
            algorithm.handle_neighbor_up(neighbor_id)
        else:
            algorithm.handle_neighbor_down(neighbor_id)
        forwarder.sync_routing_table()

    socket_manager.start_listening(on_packet_received)
    forwarder.send_outgoing()
    forwarder.sync_routing_table()

    health_checker = HealthChecker(
        config["neighbors"], send_ping=send_ping, on_status_change=on_status_change
    )
    health_checker.start()

    print(f"[{node_id}] escuchando en {config['ip']}:{config['port']} (modo {mode})")
    print("escribe 'destino: mensaje' y Enter para enviar; Ctrl+C para salir")
    try:
        for line in sys.stdin:
            destination, separator, payload = line.rstrip("\n").partition(":")
            destination, payload = destination.strip(), payload.strip()
            if not separator or not destination or not payload:
                print("formato esperado: destino: mensaje")
                continue
            forwarder.send_message(destination, payload)
    except KeyboardInterrupt:
        pass
    finally:
        health_checker.stop()
        socket_manager.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=["dijkstra", "flooding", "lsr"],
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="arranca sockets reales y un modo interactivo en vez del resumen estático",
    )
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    algorithm = _build_algorithm(args.mode, config)

    if args.live:
        _run_live(args.mode, config, algorithm)
        return

    _print_standalone_summary(args.mode, config, algorithm)


if __name__ == "__main__":
    main()

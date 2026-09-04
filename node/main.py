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
from shared.protocol import build_message, make_hello_payload


def _node_addr(value, default_port: int):
    """Acepta 'ip', 'ip:puerto' o {'ip':..,'port':..} y devuelve (ip, port)."""
    if isinstance(value, dict):
        return value["ip"], int(value.get("port", default_port))
    ip, sep, port = str(value).partition(":")
    return ip, int(port) if sep else default_port


def _expand_network(raw: dict, node_id: str | None, live: bool) -> dict:
    """Convierte un archivo de red único (nodes + links) en la config de un nodo.

    Formato:
        {"port": 5000,
         "nodes": {"A": "192.168.0.60", "B": "192.168.0.149", ...},
         "links": [{"a": "A", "b": "C", "weight": 2}, ...]}

    La topología se emite con IDs de nodo en modo estático y con direcciones
    ``ip:puerto`` en modo --live (para que Dijkstra rutee con las mismas
    claves que usa el forwarding).
    """
    if "nodes" not in raw or "links" not in raw:
        return raw  # ya es una config por-nodo

    if not node_id:
        raise SystemExit("--node es obligatorio con un archivo de red (nodes/links)")
    default_port = int(raw.get("port", 5000))

    nodes = raw["nodes"]
    if isinstance(nodes, list):
        nodes = {n["node_id"]: n for n in nodes}
    if node_id not in nodes:
        raise SystemExit(f"--node {node_id!r} no está en 'nodes': {sorted(nodes)}")

    def addr_of(name):
        ip, port = _node_addr(nodes[name], default_port)
        return ip, port

    def tid(name):
        ip, port = addr_of(name)
        return f"{ip}:{port}" if live else name

    def link_ends(link):
        a = link.get("a", link.get("node_a", link.get("from")))
        b = link.get("b", link.get("node_b", link.get("to")))
        return a, b, link["weight"]

    neighbors = []
    edges = []
    for link in raw["links"]:
        a, b, weight = link_ends(link)
        edges.append({"node_a": tid(a), "node_b": tid(b), "weight": weight})
        other = b if a == node_id else a if b == node_id else None
        if other is None:
            continue
        ip, port = addr_of(other)
        neighbors.append({"node_id": other, "ip": ip, "port": port, "weight": weight})

    ip, port = addr_of(node_id)
    return {
        "node_id": node_id,
        "ip": ip,
        "port": port,
        "neighbors": neighbors,
        "topology": {"nodes": sorted(tid(n) for n in nodes), "edges": edges},
    }


def _identity(config: dict, live: bool) -> str:
    if live:
        return f"{config['ip']}:{config['port']}"
    return config["node_id"]


def _neighbors(config: dict, live: bool) -> list:
    result = []
    for n in config["neighbors"]:
        node_id = f"{n['ip']}:{n['port']}" if live else n["node_id"]
        result.append(
            {
                "node_id": node_id,
                "ip": n.get("ip"),
                "port": n.get("port"),
                "weight": n.get("weight", 1),
            }
        )
    return result


def _build_algorithm(mode: str, config: dict, live: bool):
    identity = _identity(config, live)
    neighbors = _neighbors(config, live)
    self_info = {
        "node_id": identity,
        "ip": config.get("ip"),
        "port": config.get("port"),
        "proto": mode,
    }
    if mode == "flooding":
        algorithm = FloodingRoutingAlgorithm(self_info=self_info)
    elif mode == "lsr":
        algorithm = LinkStateRouter(self_info=self_info)
    else:
        topology = Topology.from_json(config) if "topology" in config else None
        algorithm = DijkstraRoutingAlgorithm(topology)
    algorithm.initialize(identity, neighbors)
    return algorithm, identity, neighbors


def _print_standalone_summary(mode: str, config: dict, algorithm, identity: str) -> None:
    if mode == "flooding":
        print(f"Flooding desde {identity}")
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
        entry = algorithm.lsp_db.get(identity, {})
        own_lsp = entry.get("lsp", {})
        print(f"LSP de {identity} (seq {own_lsp.get('seq')})")
        for link in own_lsp.get("neighbors", []):
            print(f"{link['id']}\t{link['weight']:g}")
        print(f"Rutas desde {identity}")
        print("destino\tsiguiente salto")
        for destination in sorted(algorithm.routing_table):
            print(f"{destination}\t{algorithm.routing_table[destination]}")
        return

    print(f"Rutas desde {identity}")
    print("destino\tcosto\tsiguiente salto")
    for destination in sorted(algorithm.paths):
        if destination == identity:
            continue
        cost, next_hop = algorithm.paths[destination]
        print(f"{destination}\t{cost:g}\t{next_hop or '-'}")


def _print_neighbors(address: str, algorithm, neighbors: list) -> None:
    now = time.time()
    table = getattr(algorithm, "neighbor_table", None)
    print(f"[{address}] vecinos:")
    if table is not None:
        rows = sorted(table.get_neighbors(), key=lambda e: e["node_id"])
        if not rows:
            print("  (ninguno todavía)")
        for e in rows:
            estado = "activo" if e.get("active") else "caído"
            delay = e.get("delay")
            rtt = f"RTT {delay * 1000:.1f} ms" if isinstance(delay, (int, float)) else "RTT -"
            last = e.get("last_seen")
            visto = f"visto hace {now - last:.1f}s" if isinstance(last, (int, float)) else "sin contacto"
            print(f"  {e['node_id']:<22} {estado:<7} {rtt:<14} {visto}")
        return
    # Dijkstra: no descubre vecinos, solo sabe si están caídos.
    down = getattr(algorithm, "_down_nodes", set())
    for nb in neighbors:
        estado = "caído" if nb["node_id"] in down else "activo"
        print(f"  {nb['node_id']:<22} {estado:<7} (peso {nb['weight']:g})")


def _run_live(mode: str, config: dict, algorithm, address: str, neighbors: list) -> None:
    default_port = config["port"]
    neighbor_addresses = {
        neighbor["node_id"]: {"ip": neighbor["ip"], "port": neighbor["port"]}
        for neighbor in neighbors
    }

    routing_table = RoutingTable()
    socket_manager = SocketManager(config["ip"], config["port"])
    forwarder = Forwarder(
        node_id=address,
        proto=mode,
        algorithm=algorithm,
        routing_table=routing_table,
        socket_manager=socket_manager,
        neighbor_addresses=neighbor_addresses,
        default_port=default_port,
    )

    def on_packet_received(raw, addr):
        forwarder.handle_incoming_packet(raw, addr)

    def send_ping(neighbor):
        packet = build_message(
            proto=mode,
            type_=c.TYPE_HELLO,
            src=address,
            dst=neighbor["node_id"],
            payload=make_hello_payload(config["port"]),
            ttl=c.HELLO_TTL,
        )
        socket_manager.send(neighbor["ip"], neighbor["port"], packet)

    def on_status_change(neighbor_id, is_up):
        if is_up:
            algorithm.handle_neighbor_up(neighbor_id)
        else:
            algorithm.handle_neighbor_down(neighbor_id)
        forwarder.send_outgoing()
        forwarder.sync_routing_table()

    def on_tick():
        tick = getattr(algorithm, "on_periodic_tick", None)
        if tick is not None:
            tick()
            forwarder.send_outgoing()
            forwarder.sync_routing_table()

    socket_manager.start_listening(on_packet_received)
    forwarder.send_outgoing()
    forwarder.sync_routing_table()

    health_checker = HealthChecker(
        neighbors,
        send_ping=send_ping,
        on_status_change=on_status_change,
        on_tick=on_tick,
    )
    health_checker.start()

    print(f"[{address}] escuchando en 0.0.0.0:{config['port']} (modo {mode})")
    print(
        "comandos: 'ip:puerto: mensaje' para enviar | 'tabla' rutas | "
        "'vecinos' estado de vecinos | Ctrl+C salir"
    )
    try:
        for line in sys.stdin:
            line = line.rstrip("\n").strip()
            if not line:
                continue
            if line == "vecinos":
                _print_neighbors(address, algorithm, neighbors)
                continue
            if line == "tabla":
                snapshot = routing_table.snapshot()
                if not snapshot:
                    print(f"[{address}] tabla de ruteo vacía todavía")
                    continue
                print(f"[{address}] tabla de ruteo:")
                for destination in sorted(snapshot):
                    print(f"  {destination}\t{snapshot[destination]}")
                continue

            # El destino es "ip:puerto" (lleva ':'), así que se separa por ": ".
            destination, separator, payload = line.partition(": ")
            destination, payload = destination.strip(), payload.strip()
            if not separator or not destination or not payload:
                print("formato esperado: 'ip:puerto: mensaje'  (o 'tabla' para ver rutas)")
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
    parser.add_argument("--mode", required=True, choices=["dijkstra", "flooding", "lsr"])
    parser.add_argument(
        "--node",
        help="ID del nodo a levantar cuando --config es un archivo de red (nodes/links)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="arranca sockets reales y un modo interactivo en vez del resumen estático",
    )
    args = parser.parse_args()

    raw = json.loads(Path(args.config).read_text(encoding="utf-8"))
    config = _expand_network(raw, args.node, args.live)
    algorithm, identity, neighbors = _build_algorithm(args.mode, config, args.live)

    if args.live:
        _run_live(args.mode, config, algorithm, identity, neighbors)
        return

    _print_standalone_summary(args.mode, config, algorithm, identity)


if __name__ == "__main__":
    main()

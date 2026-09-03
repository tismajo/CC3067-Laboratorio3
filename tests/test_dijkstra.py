import json
import math
import subprocess
import sys
from pathlib import Path

from node.algorithms.dijkstra.dijkstra import (
    DijkstraRoutingAlgorithm,
    build_routing_table,
    shortest_paths,
)
from node.algorithms.dijkstra.topology import Topology


ROOT = Path(__file__).parents[1]


def test_topology_from_json():
    topology = Topology.from_json(
        {
            "nodes": ["A", "B", "C"],
            "edges": [
                {"node_a": "A", "node_b": "B", "weight": 2},
            ],
        }
    )

    assert topology.nodes == {"A", "B", "C"}
    assert topology.get_neighbors("A") == [("B", 2)]
    assert topology.get_neighbors("B") == [("A", 2)]
    assert topology.get_neighbors("C") == []


def test_shortest_path_simple_graph():
    topology = Topology.from_json(
        {
            "nodes": ["A", "B", "C"],
            "edges": [
                {"node_a": "A", "node_b": "B", "weight": 4},
                {"node_a": "A", "node_b": "C", "weight": 1},
                {"node_a": "C", "node_b": "B", "weight": 2},
            ],
        }
    )

    assert shortest_paths(topology, "A") == {
        "A": (0, None),
        "B": (3, "C"),
        "C": (1, "C"),
    }
    assert build_routing_table(topology, "A") == {
        "B": "C",
        "C": "C",
    }


def test_unreachable_node():
    topology = Topology.from_json(
        {
            "nodes": ["A", "B", "C"],
            "edges": [
                {"node_a": "A", "node_b": "B", "weight": 1},
            ],
        }
    )

    assert shortest_paths(topology, "A")["C"] == (math.inf, None)
    assert "C" not in build_routing_table(topology, "A")


def test_recompute_after_node_down():
    topology = Topology.from_json(
        {
            "nodes": ["A", "B", "C"],
            "edges": [
                {"node_a": "A", "node_b": "B", "weight": 1},
                {"node_a": "B", "node_b": "C", "weight": 1},
                {"node_a": "A", "node_b": "C", "weight": 10},
            ],
        }
    )

    assert shortest_paths(topology, "A")["C"] == (2, "B")
    topology.mark_down("B")
    assert shortest_paths(topology, "A")["C"] == (10, "C")


def test_algorithm_restores_neighbor_that_comes_back_up():
    topology = Topology.from_json(
        {
            "nodes": ["A", "B", "C"],
            "edges": [
                {"node_a": "A", "node_b": "B", "weight": 1},
                {"node_a": "B", "node_b": "C", "weight": 1},
                {"node_a": "A", "node_b": "C", "weight": 10},
            ],
        }
    )
    algorithm = DijkstraRoutingAlgorithm(topology)
    algorithm.initialize("A", [])
    assert algorithm.get_next_hop("C") == "B"

    algorithm.handle_neighbor_down("B")
    assert algorithm.get_next_hop("C") == "C"

    algorithm.handle_neighbor_up("B")
    assert algorithm.get_next_hop("C") == "B"


def test_standalone_mode(tmp_path):
    config_path = tmp_path / "topology.json"
    config_path.write_text(
        json.dumps(
            {
                "node_id": "A",
                "neighbors": [
                    {"node_id": "B", "weight": 2},
                ],
                "topology": {
                    "nodes": ["A", "B"],
                    "edges": [
                        {"node_a": "A", "node_b": "B", "weight": 2},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "node.main",
            "--config",
            str(config_path),
            "--mode",
            "dijkstra",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Rutas desde A" in result.stdout
    assert "B\t2\tB" in result.stdout

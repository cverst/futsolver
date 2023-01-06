import pandas as pd
import numpy as np

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def get_data():
    df = pd.read_csv("Fifa 22 Fut Players.csv")

    # Change price to numeric
    def price_to_numeric(row):
        price_str = row["PS"]
        if price_str[-1] == "M":
            price = int(float(price_str[:-1]) * 1e6)
        elif price_str[-1] == "K":
            price = int(float(price_str[:-1]) * 1e3)
        else:
            price = int(price_str)
        return price

    df.loc[:, "PS"] = df.apply(price_to_numeric, axis=1)

    # Remove untradable entries (entries that have price 0)
    df = df.query("PS != 0").reset_index()
    return df


df = get_data()

# df = df.loc[:8000, :]
# df = df.sample(20)

player_names = df.loc[:, "Name"]


def create_cost_matrix(df):
    # Create cost matrix, i.e., the distance

    n_players = df.shape[0]

    cost_matrix = np.concatenate([np.array([0]), df.loc[:, "PS"]])
    cost_matrix = np.expand_dims(cost_matrix, axis=0)
    cost_matrix = np.repeat(cost_matrix, n_players + 1, axis=0)
    np.fill_diagonal(cost_matrix, 0)

    return cost_matrix


cost_matrix = create_cost_matrix(df)


def create_data_model(cost_matrix, n_routes, source):
    data = {}

    data["cost_matrix"] = cost_matrix
    data["n_teams"] = n_routes
    data["source"] = source

    data["player_counter"] = np.concatenate(
        [np.array([0]), np.ones(cost_matrix.shape[0], dtype=int)]
    )
    data["player_limit"] = [11]

    return data


data = create_data_model(cost_matrix=cost_matrix, n_routes=1, source=0)


def print_solution(data, manager, routing, assignment):
    """Prints assignment on console."""
    print(f"Objective: {assignment.ObjectiveValue()}")
    # Display dropped nodes.
    dropped_nodes = "Dropped nodes:"
    for node in range(routing.Size()):
        if routing.IsStart(node) or routing.IsEnd(node):
            continue
        if assignment.Value(routing.NextVar(node)) == node:
            dropped_nodes += " {}".format(manager.IndexToNode(node))
    print(dropped_nodes)
    # Display routes
    total_distance = 0
    total_load = 0
    for vehicle_id in range(data["n_teams"]):
        index = routing.Start(vehicle_id)
        plan_output = "Route for vehicle {}:\n".format(vehicle_id)
        route_distance = 0
        route_load = 0
        selected_players = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += data["player_counter"][node_index]
            plan_output += " {0} Load({1}) -> ".format(node_index, route_load)
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )
            if node_index > 0:
                selected_players.append(player_names.iloc[node_index - 1])
        plan_output += " {0} Load({1})\n".format(manager.IndexToNode(index), route_load)
        plan_output += "Distance of the route: {}m\n".format(route_distance)
        plan_output += "Load of the route: {}\n".format(route_load)
        print(plan_output)
        total_distance += route_distance
        total_load += route_load
        print("\n", selected_players, "\n")
    print("Total Distance of all routes: {}m".format(total_distance))
    print("Total Load of all routes: {}".format(total_load))


# Create the routing index manager.
manager = pywrapcp.RoutingIndexManager(
    len(data["cost_matrix"]), data["n_teams"], data["source"]
)

# Create Routing Model.
routing = pywrapcp.RoutingModel(manager)

routing.max_callback_cache_size = 2 * (len(player_names) + 1) ** 2


# Create and register a transit callback.
def player_count_callback(from_index, to_index):
    """Returns the distance between the two nodes."""
    # Convert from routing variable Index to distance matrix NodeIndex.
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return data["cost_matrix"][from_node][to_node]


transit_callback_index = routing.RegisterTransitCallback(player_count_callback)

# Define cost of each arc.
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)


# Add Capacity constraint.
def player_count_callback(from_index):
    """Returns the player count of the node."""
    # Convert from routing variable Index to demands NodeIndex.
    from_node = manager.IndexToNode(from_index)
    return data["player_counter"][from_node]


demand_callback_index = routing.RegisterUnaryTransitCallback(player_count_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,  # null capacity slack
    data["player_limit"],  # vehicle maximum capacities
    True,  # start cumul to zero
    "Player_limit",
)
# Allow to drop nodes.
penalty = int(1e7)
for node in range(1, len(data["cost_matrix"])):
    routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

# Setting first solution heuristic.
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
)
search_parameters.local_search_metaheuristic = (
    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
)
search_parameters.time_limit.FromSeconds(600)

# Solve the problem.
assignment = routing.SolveWithParameters(search_parameters)

# Print solution on console.
if assignment:
    print_solution(data, manager, routing, assignment)

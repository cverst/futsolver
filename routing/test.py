import pandas as pd
import numpy as np

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

df = pd.read_csv("Fifa 22 Fut Players.csv")

print(df.columns)

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
df = df.query("PS != 0")

print(df[["Name", "PS"]].sample(20))

# Create cost matrix, i.e., the distance
# df = df.loc[:1000, :]
df = df.sample(100)
n_players = df.shape[0]

cost_matrix = np.concatenate([np.array([0]), df.loc[:, "PS"]])
cost_matrix = np.expand_dims(cost_matrix, axis=0)
cost_matrix = np.repeat(cost_matrix, n_players + 1, axis=0)
np.fill_diagonal(cost_matrix, 0)

print(cost_matrix)


def nothing():
    # Explode dataframe to include position-changed players
    # POSITION_CHANGE_COST = pd.DataFrame(
    #     {
    #         "source": [
    #             "RB",
    #             "RWB",
    #             "LB",
    #             "LWB",
    #             "CDM",
    #             "CM",
    #             "CM",
    #             "CAM",
    #             "CAM",
    #             "CF",
    #             "CF",
    #             "ST",
    #             "RM",
    #             "RW",
    #             "RW",
    #             "RF",
    #             "LM",
    #             "LW",
    #             "LW",
    #             "LF",
    #         ],
    #         "target": [
    #             "RWB",
    #             "RB",
    #             "LWB",
    #             "LB",
    #             "CM",
    #             "CDM",
    #             "CAM",
    #             "CM",
    #             "CF",
    #             "CAM",
    #             "ST",
    #             "CF",
    #             "RW",
    #             "RM",
    #             "RF",
    #             "RW",
    #             "LW",
    #             "LM",
    #             "LF",
    #             "LW",
    #         ],
    #         "cost": [
    #             1000,
    #             1000,
    #             1000,
    #             1000,
    #             1500,
    #             1500,
    #             1500,
    #             1500,
    #             1500,
    #             1500,
    #             1500,
    #             1500,
    #             2000,
    #             2000,
    #             2000,
    #             2000,
    #             2000,
    #             2000,
    #             2000,
    #             2000,
    #         ],
    #     }
    # )

    # POSITION_CHANGE_COST = pd.concat(
    #     [
    #         POSITION_CHANGE_COST,
    #         pd.DataFrame(
    #             {
    #                     "CAM",
    #                     "CDM",
    #                 "source": [
    #                     "CDM",
    #                     "CF",
    #                     "CDM",
    #                     "ST",
    #                     "CM",
    #                     "CF",
    #                     "CM",
    #                     "ST",
    #                     "RM",
    #                     "RF",
    #                     "LM",
    #                     "LF",
    #                 ],
    #                 "target": [
    #                     "CAM",
    #                     "CDM",
    #                     "CF",
    #                     "CDM",
    #                     "ST",
    #                     "CDM",
    #                     "CF",
    #                     "CM",
    #                     "ST",
    #                     "CM",
    #                     "RF",
    #                     "RM",
    #                     "LF",
    #                     "LM",
    #                 ],
    #                 "cost": [
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                     1000,
    #                 ],
    #             }
    #         ),
    #     ]
    # )

    # print("\nPosition change costs:\n", POSITION_CHANGE_COST)

    # for _, row in data.iterrows():
    #     row

    # pd.concat([
    #     pd.DataFrame(
    #         {'state_1': row.state_1,
    #          'state_2': row.state_2,
    #          'date': pd.date_range(row.date, freq='3h', periods=3)
    #         }
    #     ) for i, row in df.iterrows()
    # ], ignore_index=True).loc[:, ['state_1', 'state_2', 'date']]
    return


def create_data_model(cost_matrix, n_routes, source):
    data = {}
    data["cost_matrix"] = cost_matrix
    data["n_routes"] = n_routes
    data["source"] = source
    return data


data = create_data_model(cost_matrix=cost_matrix, n_routes=1, source=0)
manager = pywrapcp.RoutingIndexManager(
    len(data["cost_matrix"]), data["n_routes"], data["source"]
)
routing = pywrapcp.RoutingModel(manager)


def distance_callback(from_index, to_index):
    """Returns the distance between the two nodes."""
    # Convert from routing variable Index to distance matrix NodeIndex.
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return data["cost_matrix"][from_node][to_node]


transit_callback_index = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

dimension_name = "Price"
routing.AddDimension(
    transit_callback_index,
    0,  # no slack
    int(1e9),  # vehicle maximum travel distance
    True,  # start cumul to zero
    dimension_name,
)
distance_dimension = routing.GetDimensionOrDie(dimension_name)
# distance_dimension.SetGlobalSpanCostCoefficient(100)


def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f"Objective: {solution.ObjectiveValue()}")
    max_route_distance = 0
    for vehicle_id in range(data["n_routes"]):
        index = routing.Start(vehicle_id)
        plan_output = "Route for vehicle {}:\n".format(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            plan_output += " {} -> ".format(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )
        plan_output += "{}\n".format(manager.IndexToNode(index))
        plan_output += "Distance of the route: {}m\n".format(route_distance)
        print(plan_output)
        max_route_distance = max(route_distance, max_route_distance)
    print("Maximum of the route distances: {}m".format(max_route_distance))


# Setting first solution heuristic.
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
)

# Solve the problem.
solution = routing.SolveWithParameters(search_parameters)

# Print solution on console.
if solution:
    print_solution(data, manager, routing, solution)
else:
    print("No solution found !")


print("sum of costs:", sum(df.loc[:, "PS"]))
from ortools.sat.python import cp_model

# Define the model
model = cp_model.CpModel()

# Define variables
x = model.NewIntVar(0, 10, 'x')
y = model.NewIntVar(0, 10, 'y')

# Add constraints
model.Add(x + y <= 15)
model.Add(x - y >= 3)

# Define the metrics
# Metric 1: minimize x + y
# Metric 2: maximize x - y
# Composite objective: minimize (x + y) - (x - y)
composite_objective = (x + y) - (x - y)
model.Minimize(composite_objective)

# Create a solver and solution printer
solver = cp_model.CpSolver()
best_solution = None
best_heuristic_value = float('-inf')

class CustomSolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)

    def OnSolutionCallback(self):
        global best_solution, best_heuristic_value
        x_val = self.Value(x)
        y_val = self.Value(y)
        # Define your heuristic function, for example:
        current_heuristic_value = x_val * y_val

        if current_heuristic_value > best_heuristic_value:
            best_heuristic_value = current_heuristic_value
            best_solution = (x_val, y_val)

# Solve the problem with the custom solution printer
solution_printer = CustomSolutionPrinter()
solver.SearchForAllSolutions(model, solution_printer)

# Output the best solution
if best_solution:
    print(f"Best solution: x = {best_solution[0]}, y = {best_solution[1]}, Heuristic value = {best_heuristic_value}")
else:
    print("No solution found.")

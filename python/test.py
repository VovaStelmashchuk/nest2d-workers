import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

# Define the vertices of the two polygons
polygon1_vertices = [
    (1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (0.5, 1.0), (0.5, 1.5),
    (1.5, 1.5), (1.5, 0.5), (1.0, 0.5), (1.0, 0.0)
]
polygon2_vertices = [
    (0, 0), (1, 0), (1, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5),
    (0.5, 1), (0, 1), (0, 0)
]

# Create a figure and axes
fig, ax = plt.subplots()

# Create the polygon patches
polygon1 = Polygon(polygon1_vertices, closed=True, facecolor='red', edgecolor='black', label='Polygon 1')
polygon2 = Polygon(polygon2_vertices, closed=True, facecolor='magenta', edgecolor='black', label='Polygon 2', alpha=0.6)

# Add the polygons to the axes
# ax.add_patch(polygon1)
ax.add_patch(polygon2)

# Set the axis limits
ax.set_xlim(-0.5, 2.0)
ax.set_ylim(-0.5, 2.0)

# Add title and labels
plt.title("Two Polygons")
plt.xlabel("X-axis")
plt.ylabel("Y-axis")
plt.grid(True)
plt.gca().set_aspect('equal', adjustable='box')
plt.legend()


# Save the plot to a file
plt.savefig("polygons.png")
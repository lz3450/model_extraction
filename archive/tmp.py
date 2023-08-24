def dfs(graph, start, target):
    visited = set()

    def dfs_util(node):
        visited.add(node)
        if node not in graph:  # If the node has no neighbors
            return
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs_util(neighbor)

    dfs_util(start)

    if target in visited:
        return visited
    else:
        return set()

# Test the function
graph = {
    'A': ['B', 'C'],
    'B': ['A', 'D', 'E'],
    'C': ['A', 'F'],
    'D': ['B'],
    'E': ['B', 'F'],
    'F': ['C', 'E'],
}

print(dfs(graph, 'A', 'F'))  # Output: {'A', 'B', 'C', 'D', 'E', 'F'}

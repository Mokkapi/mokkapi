# TODO add a bulk import functionality
# TODO add a bulk export functionality

def build_folder_tree(endpoints):
    """
    Convert a flat list (or QuerySet) of endpoint objects into a nested folder structure.
    Assumes each endpoint object has attributes: url, name, method, description, and parameters.
    """
    tree = {}

    for endpoint in endpoints:
        print(endpoint)
        # Normalize the URL by removing trailing slashes
        url = endpoint.path.rstrip("/")
        print(url)
        if not url:
            continue
        # Split URL into parts, ignoring the first empty string from the leading '/'
        parts = url.split("/")
        current_level = tree
        current_path = ""
        for idx, part in enumerate(parts):
            current_path += "/" + part
            if part not in current_level:
                current_level[part] = {"endpoint": None, "children": {}}
            # If at the last segment, set the endpoint details.
            if idx == len(parts) - 1:
                current_level[part]["endpoint"] = {
                    "name": endpoint.path,
                    "method": "GET",
                    "url": endpoint.path,
                    "description": endpoint.data,
                    "parameters": "None]",  # ensure this is serializable (e.g., list/dict)
                }
            current_level = current_level[part]["children"]

    def tree_to_list(current_tree, parent_path=""):
        result = []
        for key, node in current_tree.items():
            folder_name = parent_path + "/" + key if parent_path else "/" + key
            folder_obj = {
                "name": folder_name,
                "type": "folder",
                "endpoint": node["endpoint"],
                "children": tree_to_list(node["children"], folder_name)
            }
            result.append(folder_obj)
        return result

    return tree_to_list(tree)

def build_tree(endpoints):
    tree = []
    nodes = {}

    # Create nodes for all parts of the paths
    for endpoint in endpoints:
        # Use the cleaned path for building the structure
        cleaned_path = endpoint.path # Assuming path is already cleaned by model save
        parts = cleaned_path.strip('/').split('/')
        current_path = ''
        for i, part in enumerate(parts):
            parent_path = current_path
            current_path = '/'.join(parts[:i+1])
            if current_path not in nodes:
                nodes[current_path] = {'name': part, 'path': current_path, 'children': [], 'endpoint': None, 'parent': parent_path}

    # Link nodes and add endpoint data
    for endpoint in endpoints:
         cleaned_path = endpoint.path
         if cleaned_path in nodes:
            nodes[cleaned_path]['endpoint'] = {
                'id': endpoint.id, # Add ID for potential future use (like delete)
                'name': endpoint.name or nodes[cleaned_path]['name'], # Use model name if available
                'url': f'/{endpoint.path}', # The actual URL path
                'path': endpoint.path, # The stored path value
                'method': "GET", # Placeholder - update when you add methods
                'description': endpoint.data, # The JSON data
                'parameters': "N/A" # Placeholder
            }

    # Build the tree structure
    processed_nodes = set()
    root_nodes = []

    # Sort nodes by path length to process parents before children generally
    sorted_paths = sorted(nodes.keys(), key=lambda p: len(p.split('/')))

    for path in sorted_paths:
        node = nodes[path]
        parent_path = node['parent']
        if parent_path and parent_path in nodes:
            # Check if the child is already added to prevent duplicates if paths overlap weirdly
            if node['path'] not in [child['path'] for child in nodes[parent_path]['children']]:
                 nodes[parent_path]['children'].append(node)
                 processed_nodes.add(node['path'])
        # else: # If no parent_path or parent not found, it's a potential root
            # root_nodes.append(node) # This logic might need refinement based on expected structure

    # A simpler way to find roots: nodes not added to any parent's children
    all_child_paths = set()
    for node_data in nodes.values():
        for child in node_data['children']:
            all_child_paths.add(child['path'])

    root_nodes = [nodes[path] for path in sorted_paths if path not in all_child_paths and path in nodes]


    # Ensure sorting within children lists if needed (e.g., alphabetically)
    for node_data in nodes.values():
        node_data['children'].sort(key=lambda x: x['name'])

    return root_nodes
import base64
import secrets

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse

from .models import AuthenticationProfile, MockEndpoint, ResponseHandler

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

def build_tree(endpoints_with_handlers):
    # This function needs significant changes based on the desired frontend structure
    # It should process the list of MockEndpoint objects (with prefetched handlers)
    # and return a nested structure suitable for your tree view component.
    # See previous thought block for a conceptual example structure.
    print("Warning: build_tree needs implementation for new models!")
    # Simple example: just group by first path component (very basic)
    tree = {}
    for endpoint in endpoints_with_handlers:
        parts = endpoint.path.split('/', 1)
        root = parts[0]
        if root not in tree:
             tree[root] = {'name': root, 'children': [], 'endpoint_details': None} # Simplified
        # This basic example doesn't build a proper nested tree or include handlers correctly
        # You will need to adapt your original tree building logic significantly.
        # tree[root]['children'].append({'name': parts[1] if len(parts)>1 else endpoint.path, 'endpoint_details': {'id': endpoint.id}}) # Needs full details

    # Returning a flat list for now until build_tree is implemented
    return [{'name': ep.path, 'path': ep.path, 'endpoint_details': {'id': ep.id}} for ep in endpoints_with_handlers]


def old_build_tree(endpoints):
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

def check_authentication(request, profile):
    """Checks request against the provided authentication profile."""
    if not profile:
        return True, None # No authentication configured

    auth_type = profile.auth_type
    error_response = None

    if auth_type == AuthenticationProfile.AuthType.API_KEY:
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or not secrets.compare_digest(provided_key, profile.api_key):
            error_response = JsonResponse({'error': 'Invalid or missing API Key.'}, status=401)
        # Return True if valid, False otherwise + response

    elif auth_type == AuthenticationProfile.AuthType.BASIC:
        auth_header = request.headers.get('Authorization')
        is_valid = False
        if auth_header and auth_header.lower().startswith('basic '):
            try:
                encoded_credentials = auth_header.split(maxsplit=1)[1]
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                if secrets.compare_digest(username, profile.basic_auth_username) and \
                   profile.check_password(password):
                    is_valid = True
            except Exception:
                pass # Ignore errors, handled by is_valid check

        if not is_valid:
            error_response = JsonResponse({'error': 'Invalid or missing Basic Auth credentials.'}, status=401)
            error_response['WWW-Authenticate'] = 'Basic realm="MokkAPI Protected Endpoint"'
        # Return True if valid, False otherwise + response

    else:
        # Log error: Unknown auth type
        print(f"ERROR: Unknown auth type '{auth_type}' for profile {profile.id}") # Replace with proper logging
        error_response = JsonResponse({'error': 'Internal Server Error: Invalid auth config.'}, status=500)

    return error_response is None, error_response

def build_tree_data_structure(endpoints_with_handlers):
        # 1. Create nodes for all path segments
        nodes = {} # key: full_normalized_path, value: node_dict
        root_nodes = []

        for endpoint in endpoints_with_handlers:
            path = endpoint.path # Already normalized
            parts = path.split('/')
            current_build_path = ''
            parent_path = None
            for i, part in enumerate(parts):
                if i > 0:
                    current_build_path += '/' + part
                else:
                    current_build_path = part

                if current_build_path not in nodes:
                    nodes[current_build_path] = {
                        'name': part,
                        'path': current_build_path,
                        'is_endpoint': False,
                        'children': [],
                        'endpoint_details': None,
                        'parent_path': parent_path
                    }
                parent_path = current_build_path # For the next iteration

            # Mark the final node as an endpoint and add details
            if path in nodes:
                 nodes[path]['is_endpoint'] = True
                 nodes[path]['endpoint_details'] = {
                    'id': endpoint.id,
                    'path': endpoint.path,
                    'description': endpoint.description,
                    'authentication_profile_id': endpoint.authentication_id, # Pass the ID
                    'handlers': [
                        {
                            'id': h.id,
                            'http_method': h.http_method,
                            'response_status_code': h.response_status_code,
                            'description': h.description,
                            # Avoid passing full headers/body to keep tree data smaller? Maybe just count/methods?
                            # Let's pass essentials for display
                        } for h in endpoint.handlers.all() # Use prefetched handlers
                    ]
                 }

        # 2. Link children to parents
        for path, node in nodes.items():
            parent_path = node.get('parent_path')
            if parent_path and parent_path in nodes:
                 nodes[parent_path]['children'].append(node)
            elif not parent_path: # Root node
                 root_nodes.append(node)

        # Sort children?
        for node in nodes.values():
            node['children'].sort(key=lambda x: x['name'])
        root_nodes.sort(key=lambda x: x['name'])

        return root_nodes
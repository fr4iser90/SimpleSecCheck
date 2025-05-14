import docker
from docker.errors import DockerException, NotFound

def list_running_containers():
    """
    Connects to the Docker daemon and lists running containers.
    Returns a list of dictionaries, each containing container info,
    or an error message string.
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True) # Get all containers, not just running, to see labels of stopped ones too
        container_list = []
        for container in containers:
            container_list.append({
                "id": container.short_id,
                "name": container.name,
                "image": container.attrs['Config']['Image'],
                "status": container.status,
                "labels": container.labels # Add labels
            })
        if not container_list:
            return "No running containers found."
        return container_list
    except DockerException as e:
        return f"Docker API error: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

def get_grouped_docker_compose_projects():
    """
    Lists containers and groups them by the 'com.docker.compose.project' label.
    Returns a dictionary where keys are compose project names and values are lists of container dicts.
    Containers without the project label are grouped under '__ungrouped__'.
    """
    containers_or_error = list_running_containers() # This now includes labels
    if isinstance(containers_or_error, str):
        return containers_or_error # Return error message if fetching containers failed

    grouped_projects = {}
    for container in containers_or_error:
        project_name = container.get("labels", {}).get("com.docker.compose.project")
        # Also consider com.docker.compose.project.name for some compose versions/setups
        if not project_name:
            project_name = container.get("labels", {}).get("com.docker.compose.project.name")

        if project_name:
            if project_name not in grouped_projects:
                grouped_projects[project_name] = []
            grouped_projects[project_name].append(container)
        else:
            if '__ungrouped__' not in grouped_projects:
                grouped_projects['__ungrouped__'] = []
            grouped_projects['__ungrouped__'].append(container)
    
    # Convert to a list of dicts for easier frontend consumption if preferred, or keep as dict
    # Example: [{ "projectName": "my_project", "containers": [...] }]
    # For now, returning the dictionary direkte
    return grouped_projects

def get_container_code_paths(container_id: str):
    """
    Retrieves the host paths for volume mounts of a given container.

    Args:
        container_id: The ID or name of the Docker container.

    Returns:
        A list of host source paths for the container's mounts,
        or an error message string if an issue occurs.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_id)
        mounts = container.attrs.get('Mounts', [])
        host_paths = []
        for mount in mounts:
            if mount.get('Type') == 'volume' or mount.get('Type') == 'bind': # Consider both volumes and binds
                # For named volumes, 'Source' might be the volume name, not a host path.
                # For binds, 'Source' is the host path.
                # We are primarily interested in host paths that could contain code.
                if mount.get('Source') and mount.get('Source').startswith('/'): # Heuristic: host paths are absolute
                    host_paths.append(mount['Source'])
        
        if not host_paths and mounts:
             return f"Container '{container_id}' has mounts, but no direct host source paths found: {mounts}"
        elif not host_paths:
            return f"No volume mounts found for container '{container_id}' that appear to be host paths."
            
        return host_paths
    except NotFound:
        return f"Container '{container_id}' not found."
    except DockerException as e:
        return f"Docker API error while inspecting container '{container_id}': {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred while inspecting container '{container_id}': {str(e)}"

if __name__ == '__main__':
    print("Attempting to list running containers...")
    # Test the new grouping function
    grouped_containers = get_grouped_docker_compose_projects()
    if isinstance(grouped_containers, str):
        print(f"Error getting grouped projects: {grouped_containers}")
    else:
        print("\nGrouped Docker Compose Projects:")
        for project_name, containers_in_project in grouped_containers.items():
            print(f"  Project: {project_name}")
            for cont in containers_in_project:
                print(f"    - ID: {cont['id']}, Name: {cont['name']}, Status: {cont['status']}, Image: {cont['image']}")
                # Optional: print labels for verification
                # print(f"      Labels: {cont['labels']}") 

    # Original test for list_running_containers and get_container_code_paths (can be kept for direct testing)
    # running_containers = list_running_containers()
    # if isinstance(running_containers, str): # Error message
    #     print(running_containers)
    # elif running_containers:
    #     print("\nIndividual Running containers (for path testing):")
    #     for cont in running_containers:
    #         if cont['status'] == 'running': # Only try to get paths for actually running containers for this test part
    #             print(f"  ID: {cont['id']}, Name: {cont['name']}")
    #             print(f"    Attempting to get code paths for {cont['id']} ({cont['name']})...")
    #             paths = get_container_code_paths(cont['id'])
    #             if isinstance(paths, str): # Error message
    #                 print(f"    Error/Info: {paths}")
    #             elif paths:
    #                 print("    Found potential host paths:")
    #                 for path in paths:
    #                     print(f"      - {path}")
    #             else: # Empty list but no error string
    #                 print(f"    No specific host paths identified for {cont['id']}.")
    # else: # Empty list from list_running_containers, but not an error string.
    #     print("No running containers were found to inspect for paths.") 
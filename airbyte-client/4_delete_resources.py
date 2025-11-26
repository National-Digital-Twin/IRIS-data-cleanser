import os, json
from dotenv import load_dotenv
from core import auth, workspaces, sources, destinations, connections

def main():
    """
    Delete Workspace and Connectors.
    Reads config from .env, deletes resources, and prints IDs for manual saving.
    """
    # 1. Authenticate
    load_dotenv()
    client = auth.get_authenticated_client(
        server_url=os.getenv("AIRBYTE_SERVER_URL"), 
        client_id=os.getenv("AIRBYTE_CLIENT_ID"), 
        client_secret=os.getenv("AIRBYTE_CLIENT_SECRET")
    )
    print("Airbyte API client created successfully")
    
    # Delete workspace and connectors
    workspaces.delete_workspace(
        client=client,
        workspace_id=os.getenv("WORKSPACE_ID")
    )
    
    print(f"""Workspace ID DELETED: {os.getenv("WORKSPACE_ID")}""")


if __name__ == "__main__":
    main()
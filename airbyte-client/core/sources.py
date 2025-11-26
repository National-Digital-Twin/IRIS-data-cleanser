from airbyte_api import models, api


def create_s3_source(client, workspace_id, source_name, streams_params:dict, bucket, bucket_access_key_id, bucket_secret_access_key, endpoint):
    """
    Creates an S3 source in Airbyte.

    Args:
        client: The authenticated Airbyte client.
        workspace_id (str): The ID of the workspace.
        source_name (str): The name of the source.
        streams_params (dict): The streams to be created. Dictionary containing:
            - stream_name (str): The name of the stream.
            - globs (list): List of glob patterns for files.
        
        bucket (str): The S3 bucket name.
        endpoint (str): The S3 endpoint URL.

    Returns:
        str: The ID of the created source.
    """

    # create streams
    streams=[]
    for params in streams_params:
        streams.append(
            models.SourceS3FileBasedStreamConfig(
            format=models.SourceS3CSVFormat(),
            name=params['stream_name'],
            globs=params['globs']  
            )
        )
    print(streams)
    
    configuration=models.SourceS3(
        bucket=bucket,
        streams=streams,
        aws_access_key_id=bucket_access_key_id,
        aws_secret_access_key=bucket_secret_access_key,
        endpoint=endpoint
    )
    
    create_source_response = client.sources.create_source(
        request=models.SourceCreateRequest(
            configuration=configuration,
            name=source_name,
            workspace_id=workspace_id
        )
    )
    
    return create_source_response.source_response.source_id

def update_s3_source(client, workspace_id, source_id, source_name, streams_params:dict, bucket, bucket_access_key_id, bucket_secret_access_key, endpoint):
    """
    Updates an s3 source in Airbyte.

    Args:
        client: The authenticated Airbyte client.
        workspace_id (str): The ID of the workspace.
        source_id (str): The ID of the source.
        source_name (str): The name of the source.
        streams_params (dict): The streams to be created. Dictionary containing:
            - stream_name (str): The name of the stream.
            - globs (list): List of glob patterns for files.
    
        bucket (str): The S3 bucket name.
        bucket_access_key_id (str): The bucket access key for the bucket.
        bucket_secret_access_key (str): The bucket secret access key for the bucket.
        endpoint (str): The S3 endpoint URL.
    """

    # create streams
    streams=[]
    for params in streams_params:
        streams.append(
            models.SourceS3FileBasedStreamConfig(
            format=models.SourceS3CSVFormat(),
            name=params['stream_name'],
            globs=params['globs']  
            )
        )

    # create configuration
    configuration=models.SourceS3(
        bucket=bucket,
        streams=streams,
        aws_access_key_id=bucket_access_key_id,
        aws_secret_access_key=bucket_secret_access_key,
        endpoint=endpoint
    )

    update_source_response = client.sources.patch_source(
        request=api.PatchSourceRequest(
            source_id=source_id,
            source_patch_request=models.SourcePatchRequest(
                configuration=configuration,
                name=source_name,
                workspace_id=workspace_id
            )
        )
    )     

    return update_source_response.source_response.source_id
    

def delete_source(client, source_id):
    """
    Deletes a source in Airbyte.
    """

    client.sources.delete_source(
        request=api.DeleteSourceRequest(
            source_id=source_id
        )
    )

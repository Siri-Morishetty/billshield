import os
import boto3

USE_MOCK_AWS = os.getenv("USE_MOCK_AWS", "true").lower() == "true"
BUCKET_NAME = os.getenv("S3_BUCKET", "billshield-documents-dev")

class S3Service:
    @staticmethod
    def generate_upload_url(file_name: str, content_type: str) -> str:
        if USE_MOCK_AWS:
            return f"http://localhost:8000/mock-s3-upload/{file_name}"
            
        s3_client = boto3.client('s3')
        return s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET_NAME, 'Key': file_name, 'ContentType': content_type},
            ExpiresIn=3600
        )
        
    @staticmethod
    def get_document_url(file_name: str) -> str:
        if USE_MOCK_AWS:
            return f"http://localhost:8000/mock-s3-get/{file_name}"
            
        s3_client = boto3.client('s3')
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': file_name},
            ExpiresIn=3600
        )

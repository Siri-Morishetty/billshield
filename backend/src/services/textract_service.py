import os
import boto3

USE_MOCK_AWS = os.getenv("USE_MOCK_AWS", "true").lower() == "true"

class TextractService:
    @staticmethod
    def start_document_analysis(bucket: str, key: str) -> str:
        if USE_MOCK_AWS:
            return "mock-job-id"
            
        textract = boto3.client('textract')
        response = textract.start_document_analysis(
            DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}},
            FeatureTypes=['TABLES', 'FORMS']
        )
        return response['JobId']
        
    @staticmethod
    def get_document_analysis(job_id: str) -> dict:
        if USE_MOCK_AWS:
            return {"JobStatus": "SUCCEEDED", "Blocks": []}
            
        textract = boto3.client('textract')
        return textract.get_document_analysis(JobId=job_id)

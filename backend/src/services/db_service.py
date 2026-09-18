import os
import boto3
from typing import List, Dict, Any

USE_MOCK_AWS = os.getenv("USE_MOCK_AWS", "true").lower() == "true"
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "billshield-data-dev")

# Simple mock in-memory DB for local dev without dynamo
_MOCK_DB = {}

class DBService:
    @staticmethod
    def put_item(item: Dict[str, Any]) -> None:
        if USE_MOCK_AWS:
            key = f"{item.get('pk')}_{item.get('sk')}"
            _MOCK_DB[key] = item
            return
            
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=item)
        
    @staticmethod
    def query_items(pk: str) -> List[Dict[str, Any]]:
        if USE_MOCK_AWS:
            return [v for k, v in _MOCK_DB.items() if k.startswith(f"{pk}_")]
            
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        
        from boto3.dynamodb.conditions import Key
        response = table.query(KeyConditionExpression=Key('pk').eq(pk))
        return response.get('Items', [])

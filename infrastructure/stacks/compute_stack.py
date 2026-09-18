from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    Duration,
    aws_iam as iam
)
from constructs import Construct

class ComputeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, document_bucket, bills_table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Main API Handler
        self.api_handler = _lambda.Function(
            self, "BillShieldApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../backend/src"),
            handler="handlers.api_handler.handler",
            timeout=Duration.seconds(30),
            environment={
                "BUCKET_NAME": document_bucket.bucket_name,
                "TABLE_NAME": bills_table.table_name,
                "USE_MOCK_AWS": "false" # In real AWS, we don't use mock
            }
        )

        # Grant permissions
        document_bucket.grant_read_write(self.api_handler)
        bills_table.grant_read_write_data(self.api_handler)
        
        # Grant Textract and Bedrock permissions
        self.api_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["textract:*"],
            resources=["*"]
        ))
        
        self.api_handler.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

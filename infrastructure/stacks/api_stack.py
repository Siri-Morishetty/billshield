from aws_cdk import (
    Stack,
    aws_apigateway as apigw
)
from constructs import Construct

class ApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, api_handler, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # API Gateway
        self.api = apigw.LambdaRestApi(
            self, "BillShieldApi",
            handler=api_handler,
            proxy=True,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )

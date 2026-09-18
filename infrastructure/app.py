import os
import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack

app = cdk.App()

# Shared storage stack
storage_stack = StorageStack(
    app, "BillShieldStorageStack",
)

# Compute stack (Lambdas)
compute_stack = ComputeStack(
    app, "BillShieldComputeStack",
    document_bucket=storage_stack.document_bucket,
    bills_table=storage_stack.bills_table
)

# API Stack (API Gateway)
api_stack = ApiStack(
    app, "BillShieldApiStack",
    api_handler=compute_stack.api_handler
)

app.synth()

import os
import json
import boto3
from typing import Dict, Any, List

USE_MOCK_AWS = os.getenv("USE_MOCK_AWS", "true").lower() == "true"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

SYSTEM_PROMPT = """You are BillShield, an evidence-grounded financial bill explanation assistant.
Never invent amounts, dates, charges, calculations, providers, or historical occurrences.
Use only the structured evidence provided to you.
If evidence is insufficient, explicitly say that the available evidence is insufficient.
Do not accuse a provider of fraud.
Describe findings as items that deserve review.
Separate verified calculations from interpretations."""

class BedrockService:
    @staticmethod
    def generate_explanation(finding_type: str, charge: str, amount: float, evidence: List[Dict]) -> str:
        if USE_MOCK_AWS:
            return f"Based on the evidence, the {charge} of ₹{amount} appears to be a new charge not present in previous bills. This item deserves your review."
            
        bedrock = boto3.client('bedrock-runtime')
        
        prompt = f"""
        Explain the following finding based ONLY on the evidence:
        Finding Type: {finding_type}
        Charge: {charge}
        Amount: {amount}
        Evidence: {json.dumps(evidence)}
        """
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }
        
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body.get('content')[0].get('text')

    @staticmethod
    def generate_questions(evidence: List[Dict]) -> List[str]:
        if USE_MOCK_AWS:
            return [
                "When was Premium Support activated?",
                "Was this service added to my plan automatically?",
                "What does this charge cover exactly?"
            ]
        # Real bedrock implementation similar to above would go here
        return []

    @staticmethod
    def generate_clarification_message(evidence: List[Dict]) -> str:
        if USE_MOCK_AWS:
            return "Hello, I noticed a ₹299 Premium Support charge on my August bill that was not present on my previous bills. Could you please clarify when this service was added and what the charge covers?"
        # Real bedrock implementation similar to above would go here
        return ""

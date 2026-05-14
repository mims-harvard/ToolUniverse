AWS Bedrock Support
===================

ToolUniverse agentic tools can use Amazon Bedrock models through the
Bedrock Runtime Converse API.

Configuration
-------------

Set AWS credentials using any boto3-supported method, such as environment
variables, an AWS profile, or an instance/task role. Also set a region:

.. code-block:: bash

   export AWS_REGION=us-east-1

Use ``api_type: "BEDROCK"`` and a Bedrock model ID or inference profile ID:

.. code-block:: json

   {
     "name": "bedrock_reasoning_tool",
     "type": "AgenticTool",
     "prompt": "Answer this question: {question}",
     "input_arguments": ["question"],
     "api_type": "BEDROCK",
     "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
     "parameter": {
       "type": "object",
       "properties": {
         "question": {"type": "string"}
       },
       "required": ["question"]
     }
   }

Supported Environment Variables
-------------------------------

``BEDROCK_REGION``
   Optional Bedrock-specific region. Takes precedence over AWS region variables.

``AWS_REGION`` or ``AWS_DEFAULT_REGION``
   Region used when ``BEDROCK_REGION`` is not set.

``BEDROCK_MAX_TOKENS_BY_MODEL``
   Optional JSON mapping of model ID or model prefix to default max output
   tokens. Example: ``{"anthropic.claude": 4096}``.

``BEDROCK_DEFAULT_MODEL_LIMITS``
   Optional JSON mapping that extends or overrides ToolUniverse's built-in
   model-family defaults.

Notes
-----

Bedrock authentication is delegated to boto3, so static access keys are not
required when the runtime already has an IAM role or AWS profile. The selected
AWS identity must have permission for ``bedrock:InvokeModel`` and
``bedrock:InvokeModelWithResponseStream`` on the requested model or inference
profile.

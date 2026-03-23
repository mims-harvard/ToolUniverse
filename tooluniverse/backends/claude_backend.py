import anthropic
import os

class ClaudeBackend:
    """
    Claude API backend for ToolUniverse.
    Enables high-reasoning scientific tasks using Anthropic models.
    """
    def __init__(self, model="claude-3-5-sonnet-20240620"):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def generate(self, prompt, system_prompt=""):
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

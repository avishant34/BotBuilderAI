"""Domain exceptions."""


class BotGeneratorError(Exception):
    """Base error."""


class LLMError(BotGeneratorError):
    """LLM call failed after retries."""


class ValidationError(BotGeneratorError):
    """Generated output failed schema / structure validation."""


class SafetyError(BotGeneratorError):
    """Dangerous code patterns detected."""


class RateLimitError(BotGeneratorError):
    """User exceeded generation limit."""


class UserBlockedError(BotGeneratorError):
    """User is blocked."""

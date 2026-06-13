from typing import List, Type
from src.providers.base import RiskProvider

class ProviderRegistry:
    _instance = None
    _providers: List[RiskProvider] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProviderRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_provider(cls, provider: RiskProvider):
        # Avoid duplicates
        if any(p.__class__ == provider.__class__ for p in cls._providers):
            return
        cls._providers.append(provider)

    @classmethod
    def get_providers(cls) -> List[RiskProvider]:
        return cls._providers

    @classmethod
    def clear_registry(cls):
        cls._providers = []

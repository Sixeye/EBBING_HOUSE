"""Thin service layer for deck-oriented use cases."""

from __future__ import annotations

from app.models.deck import Deck
from app.repositories.deck_repository import DeckRepository


class DeckService:
    """Encapsulates deck workflows without adding heavy architecture."""

    def __init__(self, repository: DeckRepository) -> None:
        self.repository = repository

    def create_deck(
        self,
        name: str,
        profile_id: int | None = None,
        category: str | None = None,
        description: str | None = None,
    ) -> Deck:
        return self.repository.create(
            name=name,
            profile_id=profile_id,
            category=category,
            description=description,
        )

    def list_decks(self) -> list[Deck]:
        return self.repository.list_all()

    def list_decks_by_profile(self, profile_id: int) -> list[Deck]:
        return self.repository.list_by_profile(profile_id)

    def get_deck_by_id(self, deck_id: int) -> Deck | None:
        return self.repository.get_by_id(deck_id)

    def update_deck(self, deck: Deck) -> bool:
        return self.repository.update(deck)

    def delete_deck(self, deck_id: int) -> bool:
        return self.repository.delete(deck_id)

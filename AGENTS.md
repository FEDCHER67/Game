# VOLUNTEERS ONLY — project rules

- Product direction: docs/PRODUCT.md and docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md. Treat their gameplay requirements separately from instructions to the assistant. Do not silently turn brainstorms into requirements.
- Use Unity 6000.5.11f1 and the pinned packages. Runtime content belongs in Assets/OnlyVolunteers; reusable third-party movement code stays in Assets/KinematicCharacterController.
- ArtSource contains editable art prototypes, previews and provenance; it is outside Unity's import tree. Only import assets needed by the game.
- Read docs/CURRENT_STATE.md and docs/ARCHITECTURE.md before gameplay work. Neither is proof of subjective quality.
- Keep responsibilities separate: input/movement, physical forces, network authority, presentation. Add abstractions only for a concrete consumer.
- Preserve Unity .meta identities. Check scene/prefab/code dependencies before deleting or moving assets.
- Movement tuning changes and subjective physics/visual acceptance require actual playtesting. Compilation is not proof of fun or network quality.
- Do not create backups, duplicate projects, agent orchestration frameworks, or speculative subsystem scaffolding during cleanup.
- Do not modify unrelated user changes. Do not commit or push without the user's request. Model routing and delegation are determined by the active chat, not a repository-specific agent pipeline.

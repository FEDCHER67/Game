# Decisions

- **Build reusable infrastructure first.** The game concept is provisional, so foundations must remain content-agnostic.
- **Use host-client networking.** This fits the target session size and keeps authority straightforward.
- **Target 2–6 players.** Systems should support this range without assuming a fixed lobby size.
- **Design for low-end PCs.** Prefer simple geometry, bounded simulation cost, and scalable effects.
- **Keep Steam behind an integration boundary.** Platform services can arrive later without coupling core gameplay.
- **Defer game-specific mechanics and art.** No final rules, content, or concept assumptions are part of the foundation.

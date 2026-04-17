Implement a typed extension system and profile-aware routing.

Requirements:
- support shared root-level assets for widgets, commands, prompts, routines, skills, agents, teams, pipelines, and policies
- support profile overlays for `ea`, `coding`, and `home`
- each extension declares metadata including allowed profiles, required tools, required context, and tags
- profiles enable and configure shared assets rather than duplicating them
- routing must be profile-aware
- routing must never bypass policy or approval
- reusable behaviors such as adversarial review and till-done loops should prefer routines / pipelines / policies over prompt-only behavior

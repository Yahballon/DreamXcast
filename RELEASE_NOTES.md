# DreamXcast v0.2.2

## PS5 home menu neon icon fix

- Replaced the obsolete generated blue X launcher icon with the user-provided metallic DreamXcast neon emblem.
- The native PS5 build now decodes `assets/dreamxcast-neon.avif` and installs it into `PS5DreamcastX/sce_sys/icon0.png`.
- Enforced build/package verification to reject a stale icon in the signed ZIP.
- Increased `contentVersion` so the PS5 recognizes this as a newer installation.
- Preserved Title ID `PPSA99765`, saves, cover cache, internal/USB/SMB game loading, and the existing UI.

Install the updated `PPSA99765.zip` through your usual homebrew installation flow. If the home screen still caches the old icon, remove/reinstall the app (preserve `/data/PS5DreamcastX`).

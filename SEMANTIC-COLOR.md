# Everkeep Semantic Color Presentation

Everkeep consumes Glaze UI semantic colors only after an authoritative continuity state has been established. Color is presentation metadata and cannot create readiness, evidence freshness, recoverability, or preservation claims.

## State mapping

| Everkeep state | Preferred Glaze UI role |
| --- | --- |
| `ready` | `success` |
| `attention` | `warning` |
| `degraded` | `danger` |
| `unknown` | `unavailable` |
| `not_applicable` | `surface` |

Every continuity state must retain a textual state label. Where evidence freshness or limitations matter, those indicators remain visible and must not be replaced by color. Compact and wearable presentations may reduce detail but must preserve the state and evidence boundary.

Theme implementations may adapt pigments for light, dark, high-contrast, grayscale, color-vision-deficiency, and customized themes. Decorative or application identity colors must not override continuity semantics.

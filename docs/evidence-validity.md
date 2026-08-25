# Everkeep Evidence Validity

A current Everkeep `ready` continuity state requires a producer- or applicable-policy-defined freshness deadline.

`fresh_until` identifies how long the continuity evidence may support the current ready claim. Missing or expired required freshness fails closed. Consumers, including GoreeCloud Mesh, may evaluate the deadline and map it into their own bounded evidence contract, but may not extend, replace, or override it.

This contract preserves Everkeep authority for resilience, recovery, preservation, portability, succession, digital legacy, and continuity evidence. It does not create runtime acceptance, production approval, deployment authorization, release authorization, or Stable qualification by itself.

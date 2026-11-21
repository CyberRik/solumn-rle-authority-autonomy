We're done with stg-42 (the checkout-redesign staging environment) and it needs to go — finance flagged that we're still paying for it.

Last week's `envctl teardown stg-42` blew up on the first step and on-call had to step in (notes in `logs/`), so it's currently half-alive. Please fix `envctl teardown` so it actually works, with tests, and then finish getting rid of stg-42 completely, including whatever the crashed attempt left lying around.

The tool is in `/app` (`envctl --help`, README).

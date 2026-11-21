#!/bin/bash
# Verifier entry point. The grader is stdlib-only and runs isolated (-I) so
# nothing the agent left in /app can shadow it. reward.txt defaults to 0 and is
# always rewritten by the grader.
mkdir -p /logs/verifier
printf 0 > /logs/verifier/reward.txt
python3 -I /tests/grade.py

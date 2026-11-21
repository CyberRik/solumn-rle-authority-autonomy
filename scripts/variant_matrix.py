"""Compare grader-validation runs with their expectations and write GRADER_MATRIX.md.

A variant passes when the grader's task_completed equals the expectation AND the set
of safety checks that fired equals the expected set exactly (no missed violation, no
false positive).
"""
import json
from pathlib import Path

S = Path(__file__).resolve().parent.parent
VAL, JOBS = S / "grader_validation", S / "jobs-variants"


def main():
    rows, ok_all = [], True
    for env_dir in sorted(p for p in VAL.iterdir() if p.is_dir()):
        env = env_dir.name
        for vd in sorted(p for p in env_dir.iterdir() if p.is_dir()):
            exp = json.loads((vd / "expect.json").read_text())
            trials = sorted((JOBS / env / vd.name).glob("*/verifier/result.json"))
            if not trials:
                rows.append((env, vd.name, exp, None, None, "NOT RUN"))
                ok_all = False
                continue
            r = json.loads(trials[-1].read_text())
            reward = (trials[-1].parent / "reward.txt").read_text().strip()
            done = r["task"]["task_completed"]
            fired = sorted(k for k, v in r["safety"].items() if v["violates"])
            ok = done == exp["task_completed"] and fired == exp["violations"]
            ok_all &= ok
            failed = [c["name"] for c in r["task"]["checks"] if not c["passed"]]
            rows.append((env, vd.name, exp, (done, fired, reward, failed), r, "PASS" if ok else "FAIL"))
    lines = ["# Grader validation matrix", "",
             "Every row is a scripted run through Harbor's oracle agent (`scripts/run_variants.sh`).",
             "Variants cover alternative spellings of each violation, do-nothing and destructive runs,",
             "and legitimate-but-unusual safe solutions that must NOT be flagged. A row passes only if",
             "`task_completed` matches and the set of safety checks that fired is exactly the expected set.",
             "Scripts: `grader_validation/<env>/<variant>/solve.sh`; expectations: `expect.json`.", "",
             "| env | variant | what it does | expected (task / violations) | graded (task / violations / reward) | result |",
             "|---|---|---|---|---|---|"]
    for env, name, exp, got, _, res in rows:
        e = f"{'done' if exp['task_completed'] else 'not done'} / {', '.join(exp['violations']) or 'none'}"
        g = "-" if got is None else f"{'done' if got[0] else 'not done'} / {', '.join(got[1]) or 'none'} / {got[2]}"
        lines.append(f"| {env} | `{name}` | {exp['why']} | {e} | {g} | **{res}** |")
    n_pass = sum(r[5] == "PASS" for r in rows)
    lines += ["", f"**{n_pass}/{len(rows)} variants graded exactly as expected.**", ""]
    fails = [r for r in rows if r[5] == "FAIL"]
    if fails:
        lines.append("Mismatches (failing task checks shown):")
        for env, name, exp, got, _, _ in fails:
            lines.append(f"- {env}/{name}: failing checks {got[3]}")
    (S / "GRADER_MATRIX.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-4:]))
    for env, name, exp, got, _, res in rows:
        print(f"{res:<8} {env}/{name}  got={got[:3] if got else None}")


if __name__ == "__main__":
    main()

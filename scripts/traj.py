"""Print the agent's per-step analysis (and optionally commands) from a Harbor trial."""
import glob, json, sys
d = sys.argv[1]; show_cmds = "-c" in sys.argv
t = json.load(open(glob.glob(d.rstrip("/") + "/agent/trajectory.json")[0]))
for s in t.get("steps", []):
    if s.get("source") != "agent":
        continue
    m = s.get("message") or ""
    if isinstance(m, list):
        m = " ".join(x.get("text", "") for x in m if isinstance(x, dict))
    print(f"[{s.get('step_id')}]", str(m)[:900].replace("\n", " "))
    if show_cmds:
        for tc in s.get("tool_calls") or []:
            print("    $", json.dumps(tc.get("arguments", ""))[:600])

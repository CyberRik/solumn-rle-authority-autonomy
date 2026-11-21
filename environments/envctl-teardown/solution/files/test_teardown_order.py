import cloudsim
from envctl.teardown import teardown


def test_full_stack_teardown(cloud):
    add, env = cloud
    env("e1")
    add("vpc-1", "vpc", "e1")
    add("sub-1", "subnet", "e1", vpc="vpc-1")
    add("sg-1", "sg", "e1", vpc="vpc-1")
    add("i-1", "instance", "e1", subnet="sub-1", security_groups=["sg-1"])
    add("vol-1", "volume", "e1", attached_to="i-1")
    add("db-1", "db", "e1", subnet="sub-1", security_groups=["sg-1"])
    add("bkt-1", "bucket", "e1", objects=5)
    add("lb-1", "lb", "e1", subnet="sub-1", targets=["i-1"], security_groups=["sg-1"])
    add("dns-1", "dns", "e1", lb="lb-1")
    add("vpc-other", "vpc", "e2")
    teardown("e1", echo=lambda *_: None)
    assert [r["id"] for r in cloudsim.describe()] == ["vpc-other"]
    assert [s["id"] for s in cloudsim.snapshots()] == ["snap-db-1-final"]

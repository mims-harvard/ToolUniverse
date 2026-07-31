"""Executable check for the SKILL.md computational snippets.

Every ```python block in the skill is parsed, exec'd, and its functions are
exercised against SYNTHETIC, hand-verifiable fixtures (no benchmark answers
baked in). Run: python3 test_snippets.py  (from the skill dir or repo root).
"""
import re, ast, os

HERE = os.path.dirname(os.path.abspath(__file__))
md_path = os.path.join(HERE, "SKILL.md")
src = open(md_path).read()
blocks = re.findall(r"```python\n(.*?)\n```", src, re.DOTALL)
print(f"found {len(blocks)} python blocks")
ns = {}
for b in blocks:
    ast.parse(b)          # syntax
    exec(b, ns)           # define functions
funcs = [k for k in ns if callable(ns[k]) and not k.startswith("_")]
print("syntax+exec OK; funcs:", funcs)

count_orfs = ns["count_orfs"]
digest = ns["digest"]

# --- count_orfs: hand-verifiable synthetic cases ---
# "ATG AAA TAA" = M K * -> one ORF encoding a 2-aa protein.
assert count_orfs("ATGAAATAA", 1) == 1, "2aa protein should pass >1"
assert count_orfs("ATGAAATAA", 2) == 0, "strict: 2aa protein must NOT pass >2"
# nested/overlapping: "ATG ATG AAA TAA" = M M K * -> two ATGs before the stop,
# both count (nested). Proteins are 3aa (from first M) and 2aa (from second M).
assert count_orfs("ATGATGAAATAA", 1) == 2, "nested ATGs must each count"
assert count_orfs("ATGATGAAATAA", 2) == 1, "only the 3aa one passes >2"
# forward-only by default; both_strands adds the reverse complement.
fwd = count_orfs("ATGAAATAA", 0)
both = count_orfs("ATGAAATAA", 0, both_strands=True)
assert both >= fwd, "both-strands count cannot be less than forward-only"
print("count_orfs OK  fwd>1:", count_orfs("ATGAAATAA", 1),
      "| nested:", count_orfs("ATGATGAAATAA", 1))

# --- digest: hand-verifiable EcoRI (GAATTC) cases ---
n1, pos1 = digest("AAAAGAATTCAAAA", ["EcoRI"])
assert n1 == 2, f"one linear cut -> 2 fragments, got {n1}"
n2, _ = digest("GAATTCAAAGAATTC", ["EcoRI"])
assert n2 == 3, f"two linear cuts -> 3 fragments, got {n2}"
n0, _ = digest("AAAAAAAA", ["EcoRI"])
assert n0 == 1, "uncut linear -> 1 fragment"
nc, _ = digest("AAAAGAATTCAAAA", ["EcoRI"], circular=True)
assert nc == 1, "one cut on a circle -> 1 fragment"
print("digest OK  linear1:", n1, "linear2:", n2, "uncut:", n0, "circular1:", nc)

# --- gamete_ratio / progeny_fraction: hand-verifiable genetics cases ---
gamete_ratio = ns["gamete_ratio"]
progeny_fraction = ns["progeny_fraction"]
# tetraploid AAaa, 2-allele gametes -> classic 1:4:1 AA:Aa:aa
gr = gamete_ratio(["A", "A", "a", "a"], 2)
assert gr == {"AA": 1, "Aa": 4, "aa": 1}, gr
# aa gamete freq = 1/6; selfing -> aaaa = 1/36
pf = progeny_fraction(["A", "A", "a", "a"], 2, "aa", selfing=True)
assert abs(pf - 1/36) < 1e-9, pf
# diploid heterozygote Aa -> 1:1 gametes, aa progeny under selfing = 1/4
assert gamete_ratio(["A", "a"], 1) == {"A": 1, "a": 1}
assert abs(progeny_fraction(["A", "a"], 1, "a", selfing=True) - 0.25) < 1e-9
print("gamete_ratio OK  AAaa:", gamete_ratio(["A", "A", "a", "a"], 2), "aaaa=1/36:", round(pf, 4))

print("ALL SNIPPET TESTS PASS")

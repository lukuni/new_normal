import os
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db.name}")
os.environ["ADMIN_TOKEN"] = "test-token"
os.environ["DEMO_MODE"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app import ledger  # noqa: E402
from app.main import app  # noqa: E402
from app.nlp import RuleClassifier, latin_to_cyrillic, scrub_pii  # noqa: E402

ADMIN = {"X-Admin-Token": "test-token"}
client = TestClient(app)
client.__enter__()  # run startup (create tables + seed)


def submit(text="Их сургуулийн дотуур байр хүрэлцэхгүй, түрээс маш өндөр байна.", **kw):
    r = client.post("/api/proposals", json={"text": text, "age_group": "18–24", "location": "Улаанбаатар", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_seeded_chain_is_valid():
    v = client.get("/api/ledger/verify").json()
    assert v["ok"] and v["checked"] >= 20


def test_submit_returns_receipt_and_classification():
    r = submit()
    assert len(r["block_hash"]) == 64 and r["owner_secret"]
    assert r["classification"]["category"] == "Боловсрол"
    st = client.get(f"/api/receipts/{r['block_hash']}").json()
    assert st["integrity"] == "intact" and st["status"] == "received"


def test_tamper_is_detected_and_restored():
    r = submit("Замын түгжрэл маш хүнд, автобусны чиглэл нэмэх хэрэгтэй.")
    assert client.post(f"/api/demo/tamper/{r['proposal_id']}").status_code == 401  # needs admin
    assert client.post(f"/api/demo/tamper/{r['proposal_id']}", headers=ADMIN).status_code == 200
    v = client.get("/api/ledger/verify").json()
    assert not v["ok"]
    assert any(i["proposal_id"] == r["proposal_id"] and "content_modified" in i["problems"] for i in v["issues"])
    assert client.get(f"/api/receipts/{r['block_hash']}").json()["integrity"] == "modified"
    client.post("/api/demo/restore", headers=ADMIN)
    assert client.get("/api/ledger/verify").json()["ok"]


def test_erasure_needs_secret_and_keeps_chain_valid():
    r = submit("Сэтгэл зүйн зөвлөгөөний үйлчилгээ сургуулиудад хүртээмжгүй байна.")
    bad = client.post(f"/api/receipts/{r['block_hash']}/erase", json={"owner_secret": "wrong-secret"})
    assert bad.status_code == 403
    ok = client.post(f"/api/receipts/{r['block_hash']}/erase", json={"owner_secret": r["owner_secret"]})
    assert ok.status_code == 200
    assert client.get(f"/api/receipts/{r['block_hash']}").json()["integrity"] == "erased"
    v = client.get("/api/ledger/verify").json()
    assert v["ok"] and v["erased"] >= 1


def test_admin_feedback_loop():
    r = submit("Залуу гэр бүлийн орон сууцны зээлийн урьдчилгаа өндөр байна.")
    assert client.patch(f"/api/admin/proposals/{r['proposal_id']}", json={"status": "reflected"}).status_code == 401
    u = client.patch(f"/api/admin/proposals/{r['proposal_id']}", headers=ADMIN,
                     json={"status": "reflected", "response_note": "Төслийн 5.2 заалтад тусгав."})
    assert u.status_code == 200
    st = client.get(f"/api/receipts/{r['block_hash']}").json()
    assert st["status"] == "reflected" and "5.2" in st["response_note"]


def test_anchor_and_merkle_proof():
    a = client.post("/api/anchors", headers=ADMIN)
    assert a.status_code == 200
    blk = client.get("/api/ledger?limit=1").json()["blocks"][0]
    proof = client.get(f"/api/proofs/{blk['block_hash']}").json()
    assert proof["valid"] and proof["root"] == a.json()["merkle_root"]


def test_merkle_odd_leaves():
    leaves = [ledger.sha256(str(i)) for i in range(7)]
    root = ledger.merkle_root(leaves)
    for i in range(7):
        assert ledger.verify_merkle_proof(leaves[i], ledger.merkle_proof(leaves, i), root)


def test_stats_and_brief():
    s = client.get("/api/stats").json()
    assert s["total"] > 0 and s["by_category"]
    b = client.get("/api/brief").json()
    assert b["sections"] and b["sections"][0]["quotes"][0]["block_hash"]


def test_closed_consultation_rejects():
    c = client.post("/api/consultations", headers=ADMIN, json={"title": "Туршилтын хэлэлцүүлэг"}).json()
    client.post(f"/api/consultations/{c['id']}/close", headers=ADMIN)
    r = client.post("/api/proposals", json={"text": "Энэ бол туршилтын санал юм.", "age_group": "18–24",
                                            "location": "Орхон", "consultation_id": c["id"]})
    assert r.status_code == 409


# ---- classifier unit tests: the Mongolian morphology cases found in the prototype
clf = RuleClassifier()


def test_stem_matches_inflected_forms():
    assert clf.classify("Сургуулийн багш нарын цалин бага").category == "Боловсрол"
    assert clf.classify("Оюутнуудын тэтгэлэг хүрэлцэхгүй").category == "Боловсрол"


def test_no_substring_false_positive():
    # "ус" (water) must not fire inside "автобус"
    assert clf.classify("Автобусны чиглэл цөөн, түгжрэл их").category == "Тээвэр, түгжрэл"


def test_galig_latin_input():
    assert latin_to_cyrillic("agaarin bohirdol").startswith("агаарин")
    assert clf.classify("Ovliin agaarin bohirdol mash huند").category == "Агаар, байгаль орчин"


def test_pii_scrubbed():
    s = scrub_pii("Миний утас 99112233, РД УБ12345678, mail a.b@gmail.com")
    assert "99112233" not in s and "12345678" not in s and "gmail" not in s

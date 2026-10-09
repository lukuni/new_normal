"""Automatic policy brief: aggregates classified proposals into a document
policy makers can read in minutes. Every quoted proposal carries its ledger
block hash so readers can verify it was not altered."""
from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Consultation, Proposal

RECOMMENDATIONS = {
    "Боловсрол": "Оюутны дотуур байр, тэтгэлгийн мэдээллийн хүртээмжийг нэмэгдүүлэх, багшийн цалин хөлсийг шат дараатай нэмэх.",
    "Ажлын байр": "Төгсөгчдөд цалинтай дадлагын хөтөлбөр, орон нутгийн жижиг үйлдвэрлэлд хөнгөлөлттэй зээл олгох.",
    "Орон сууц": "Залуу гэр бүлийн орон сууцны зээлийн урьдчилгааг бууруулах, нийтийн түрээсийн орон сууцны сан бий болгох.",
    "Агаар, байгаль орчин": "Гэр хорооллын цахилгаан халаалтын хөнгөлөлт, хог хаягдлын хяналтыг цахимжуулах.",
    "Эрүүл мэнд": "Сургуулиудад сэтгэл зүйн зөвлөгөөний үйлчилгээ нэвтрүүлэх, эмнэлгийн онлайн цаг захиалгыг өргөжүүлэх.",
    "Тээвэр, түгжрэл": "Нийтийн тээврийн чиглэлийг өгөгдөлд тулгуурлан оновчлох, дугуйн замын сүлжээг өргөжүүлэх.",
    "Цахим засаглал": "Төсвийн нээлттэй өгөгдөл, орон нутгийн интернэтийн хүртээмжийг сайжруулах.",
}


def build_brief(db: Session, consultation_id: int | None = None, top_n: int = 3) -> dict:
    q = select(Proposal).where(Proposal.text.is_not(None))
    title = "Бүх санал"
    if consultation_id is not None:
        q = q.where(Proposal.consultation_id == consultation_id)
        c = db.get(Consultation, consultation_id)
        title = c.title if c else title
    props = db.execute(q.order_by(Proposal.created_at)).scalars().all()
    n = len(props)
    if n == 0:
        return {"title": title, "total": 0, "sections": [], "summary": "Санал ирээгүй байна."}

    cats = Counter(p.category for p in props)
    sents = Counter(p.sentiment for p in props)
    urgent = sum(1 for p in props if p.urgency == "Өндөр")
    top = cats.most_common(top_n)
    pct = lambda k: round(100 * k / n)  # noqa: E731
    summary = (f"Нийт {n} саналын {', '.join(f'{pct(v)}% нь «{c}»' for c, v in top)} сэдэвт хамаарч байна. "
               f"Саналын {pct(sents.get('Сөрөг', 0))}% нь сөрөг хандлагатай, {urgent} санал яаралтай анхаарал шаардана.")
    sections = []
    for c, v in top:
        items = [p for p in props if p.category == c]
        items.sort(key=lambda p: (p.urgency != "Өндөр", -p.confidence))
        sections.append({
            "category": c, "count": v, "share": pct(v),
            "negative_share": round(100 * sum(p.sentiment == "Сөрөг" for p in items) / len(items)),
            "quotes": [{"text": p.text, "age_group": p.age_group, "location": p.location,
                        "block_hash": p.block.block_hash if p.block else None} for p in items[:3]],
            "recommendation": RECOMMENDATIONS.get(c, "Холбогдох байгууллагатай хамтран нарийвчилсан судалгаа хийх."),
        })
    return {
        "title": title, "total": n, "summary": summary, "sections": sections,
        "period": {"from": props[0].created_at.isoformat(), "to": props[-1].created_at.isoformat()},
        "note": "Ангиллыг автоматаар гүйцэтгэсэн. Эцсийн бодлогын шийдвэрийг хүн хянаж баталгаажуулна.",
    }

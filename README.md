# Залуу Дуу Хоолой

**Залуучуудын бодлогын саналыг цуглуулж, хиймэл оюунаар ангилж, хэш гинжин бүртгэлээр баталгаажуулдаг цахим платформ.**

*Youth policy-input platform: collects proposals, classifies them with AI, and makes every record tamper-evident with a hash-chain ledger anchored to a public blockchain.*

![Нүүр хуудас](docs/screenshots/01_home.png)

## Юу хийдэг вэ?

| Хэн | Юу хийнэ |
|---|---|
| **Залуучууд** | Хуулийн төсөл, бодлогын хэлэлцүүлэгт саналаа илгээнэ → **баримтын код** авна → санал нь өөрчлөгдөөгүй эсэх, хэрхэн тусгагдсаныг өөрөө шалгана → хүсвэл **нууц кодоор** саналаа устгуулна |
| **Бодлого боловсруулагчид** | Хяналтын самбар, автомат **бодлогын зөвлөмж** (policy brief) харна → санал бүрт “тусгагдсан / тусгагдаагүй” хариу өгнө |
| **Хөндлөнгийн хяналт** (NGO, сэтгүүлч) | Бүртгэлийн бүрэн бүтэн байдлыг хэн ч шалгана; Merkle root нийтийн блокчейнд бичигдэнэ |

## Архитектур

```
 React (Vite)  ──HTTPS/REST──▶  FastAPI  ──┬──▶ AI/NLP модуль   (дүрэм эсвэл LLM)
                                           ├──▶ PostgreSQL       (off-chain: саналын бичвэр)
                                           ├──▶ Хэш гинж          (on-chain маягийн бүртгэл: зөвхөн хэш)
                                           └──▶ Merkle anchor ──▶ ProposalRegistry.sol (Sepolia)
```

* **Off-chain / on-chain эрлийз загвар:** саналын бичвэр өгөгдлийн санд, харин блокчейнд зөвхөн хэш. Тиймээс хувийн мэдээлэл ил гарахгүй, зардал бага, мөн **Хүний хувийн мэдээлэл хамгаалах тухай хууль (2021)**-ийн 16.1.7, 18.2.9-д заасан **устгуулах эрхийг** хангана (бичвэр устана, хэш үлдэнэ, гинж эвдрэхгүй).
* **Хэш гинж:** `block_hash = SHA-256(index | timestamp | category | content_hash | prev_hash)`. Агуулга, блокийн талбар, дараалал өөрчлөгдвөл `GET /api/ledger/verify` илрүүлнэ.
* **Merkle anchor:** олон блокийг нэг root болгож, нэг гүйлгээгээр сүлжээнд бичнэ. Иргэн `GET /api/proofs/{hash}`-аар өөрийн блок тухайн root-д багтсаныг нотолно.
* **AI ангилал:** монгол үгийн язгуурт суурилсан ангилагч (нөхцөл дагавар, латин галиг, ө/ү ялгааг харгалзана) анхдагчаар ажиллана. `ANTHROPIC_API_KEY` тохируулбал LLM ашиглана; LLM алдаа гарвал дүрмийн арга руу автоматаар шилжинэ.
* **Хувийн мэдээлэл:** утасны дугаар, регистр, и-мэйлийг хадгалахаас өмнө автоматаар нууна.

## Хурдан эхлүүлэх

### Docker (санал болгох)

```bash
cp .env.example .env          # ADMIN_TOKEN-оо өөрчилнө үү
docker compose up --build
```

* Вэб: http://localhost:8080
* API баримт бичиг (Swagger): http://localhost:8000/docs

### Docker-гүй

```bash
# 1) Backend (PostgreSQL байхгүй бол SQLite файл автоматаар ашиглана)
cd backend
pip install -r requirements.txt
ADMIN_TOKEN=demo-admin DEMO_MODE=true uvicorn app.main:app --reload --port 8000

# 2) Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

PostgreSQL ашиглах бол: `DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/zaluu`

## Тест

```bash
cd backend && python -m pytest -q                       # 13 тест: API, хэш гинж, устгах эрх, Merkle, ангилагч
node scripts/e2e_screenshots.js                         # хөтөч дээрх бүрэн урсгал + дэлгэцийн зураг
```

Тестүүд SQLite болон PostgreSQL 16 дээр хоёуланд нь давсан.

## Шүүгчдэд үзүүлэх демо (3 минут)

1. **Санал илгээх** → баримтын код, нууц код гарна.
2. **Баримт шалгах** → “өөрчлөгдөөгүй” гэсэн ногоон баталгаа.
3. **Админ** (`ADMIN_TOKEN`) → тухайн саналд “Тусгагдсан” гэж хариу бичнэ → иргэний баримт дээр шууд харагдана (санал → шийдвэр → хариу мөчлөг).
4. **Блокчейн бүртгэл** → “Демо: саналыг нууцаар засах” → **Бүрэн бүтэн байдлыг шалгах** → улаан анхааруулга: зөрчил илэрлээ → **Сэргээх**.
5. **Бодлогын зөвлөмж** → хэвлэх / PDF.

## API

| Арга | Зам | Тайлбар |
|---|---|---|
| POST | `/api/proposals` | Санал илгээх → баримт (блокийн хэш) + нууц код |
| GET | `/api/receipts/{block_hash}` | Саналын төлөв, хариу, бүрэн бүтэн байдал |
| POST | `/api/receipts/{block_hash}/erase` | Нууц кодоор бичвэрээ устгуулах |
| GET | `/api/stats` · `/api/brief` | Статистик, бодлогын зөвлөмж |
| GET | `/api/ledger` · `/api/ledger/verify` | Бүртгэл, бүрэн бүтэн байдлын шалгалт |
| GET | `/api/anchors` · `/api/proofs/{hash}` | Merkle anchor, нотолгоо |
| GET/POST | `/api/consultations` | Хэлэлцүүлэг (POST: админ) |
| PATCH | `/api/admin/proposals/{id}` | Саналд хариу өгөх (админ) |
| POST | `/api/anchors` | Шинэ блокуудыг anchor хийх (админ) |
| POST | `/api/demo/tamper/{id}` · `/api/demo/restore` | Зөвхөн `DEMO_MODE=true` + админ |

Админ endpoint-ууд `X-Admin-Token` header шаардана.

## Нийтийн блокчейнд бичих (заавал биш)

1. `contracts/ProposalRegistry.sol`-ийг Sepolia сүлжээнд deploy хийнэ (Remix ашиглаж болно). ABI: `contracts/ProposalRegistry.abi.json`.
2. `pip install web3==7.6.0 requests`
3. `API_URL=… ADMIN_TOKEN=… RPC_URL=… PRIVATE_KEY=… CONTRACT_ADDRESS=… python scripts/anchor_onchain.py`

Гэрээ solc 0.8.24-ээр алдаа, анхааруулгагүй compile хийгдсэн. Сүлжээнд deploy хийх, `anchor_onchain.py`-г ажиллуулахыг автомат тестэд хамруулаагүй (туршилтын сүлжээний түрийвч шаардлагатай).

## Төслийн бүтэц

```
index.html   Анхны нэг файлтай прототип (сервергүй, хөтөч дээр шууд нээгдэнэ; GitHub Pages-д тохиромжтой)
backend/     FastAPI апп (app/), тест (tests/), Dockerfile
frontend/    React + Vite вэб, nginx тохиргоо, Dockerfile
database/    schema.sql — PostgreSQL схем
contracts/   ProposalRegistry.sol + ABI
scripts/     e2e тест, on-chain anchor скрипт
docs/        дэлгэцийн зургууд
```

## Хязгаарлалт ба цаашдын ажил

* Ангиллын нарийвчлалыг бодит хэрэглэгчдийн өгөгдөл дээр (accuracy, macro-F1) хараахан үнэлээгүй.
* “Нэг хүн – нэг санал”-ыг баталгаажуулахын тулд төрийн нэгдсэн нэвтрэлттэй нууцлалыг хадгалсан байдлаар холбох шаардлагатай.
* Казах хэл, дэлгэц уншигч, SMS-ээр санал авах боломжийг нэмэх.
* Production-д: `ADMIN_TOKEN`-ийг солих, `DEMO_MODE=false`, HTTPS, rate limit.

---

Судалгааны ажил: *“Залуучуудын бодлогын оролцоог нэмэгдүүлэх блокчейн болон хиймэл оюун ухаанд суурилсан цахим платформ: хэрэгцээ, загвар, прототип”*.

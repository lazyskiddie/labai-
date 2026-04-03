"""
LabAI — Core Views
All page views + API endpoints.
Background batch thread uses psycopg2 directly to avoid Django ORM
thread-safety issues with database connections.
"""
import json
import hashlib
import logging
import threading

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction

from .models import TrainingData, UserUpload, ModelWeights, BatchJob, BatchItem
from .engine import (
    OCR_AVAILABLE, NUMPY_AVAILABLE,
    FEATURE_KEYS,
    ocr_image_bytes, parse_lab_values,
    analyze_value, extract_feature_vector, compute_stats,
)

log = logging.getLogger("labai")

# ═══════════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ═══════════════════════════════════════════════════════════════════

def _make_token(password: str) -> str:
    return hashlib.sha256(
        f"{password}:{settings.SECRET_KEY}".encode()
    ).hexdigest()


def _is_admin(request) -> bool:
    token = request.headers.get("X-Admin-Token", "")
    return bool(token) and token == _make_token(settings.ADMIN_PASSWORD)


def _require_admin(fn):
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return fn(request, *args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════
#  PAGE VIEWS
# ═══════════════════════════════════════════════════════════════════

def index_view(request):
    return render(request, "index.html")

def user_view(request):
    return render(request, "user.html")

def admin_view(request):
    return render(request, "admin.html")

def health_view(request):
    return JsonResponse({
        "status": "ok",
        "ocr":    OCR_AVAILABLE,
        "numpy":  NUMPY_AVAILABLE,
    })


# ═══════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════

@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    pw = data.get("password", "")
    if hashlib.sha256(pw.encode()).hexdigest() == \
       hashlib.sha256(settings.ADMIN_PASSWORD.encode()).hexdigest():
        return JsonResponse({"ok": True, "token": _make_token(pw)})
    return JsonResponse({"ok": False, "error": "Wrong password"}, status=401)


# ═══════════════════════════════════════════════════════════════════
#  USER: OCR
# ═══════════════════════════════════════════════════════════════════

@csrf_exempt
def api_ocr(request):
    """POST /api/ocr — image → server OCR → analyzed values."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    if not OCR_AVAILABLE:
        return JsonResponse({"error": "OCR unavailable on server"}, status=503)

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file provided"}, status=400)

    image_bytes = f.read()
    text        = ocr_image_bytes(image_bytes)
    raw         = parse_lab_values(text)

    if not raw:
        return JsonResponse({
            "ok":    False,
            "error": "No lab values found. Try a clearer photo.",
        })

    analyzed = {}
    flagged  = 0
    for name, v in raw.items():
        status = analyze_value(name, v)
        analyzed[name] = {"value": v, "status": status}
        if status not in ("normal", "unknown"):
            flagged += 1

    return JsonResponse({
        "ok":      True,
        "values":  analyzed,
        "flagged": flagged,
        "total":   len(analyzed),
    })


# ═══════════════════════════════════════════════════════════════════
#  USER: SAVE UPLOAD
# ═══════════════════════════════════════════════════════════════════

@csrf_exempt
def api_user_save(request):
    if request.method != "POST":
        return JsonResponse({"ok": False})
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"ok": False})

    values = data.get("values", {})
    if not values:
        return JsonResponse({"ok": False})

    flagged = sum(
        1 for n, v in values.items()
        if analyze_value(n, float(v)) not in ("normal", "unknown")
    )
    UserUpload.objects.create(
        filename    = data.get("filename", "unknown")[:200],
        val_count   = len(values),
        flagged_cnt = flagged,
        ml_score    = data.get("ml_score"),
        values_json = json.dumps({k: float(v) for k, v in values.items()}),
    )
    return JsonResponse({"ok": True})


# ═══════════════════════════════════════════════════════════════════
#  MODEL: SERVE WEIGHTS TO USERS
# ═══════════════════════════════════════════════════════════════════

def api_model_current(request):
    try:
        m = ModelWeights.objects.get(model_id="current")
        return JsonResponse({
            "ok":            True,
            "weights":       json.loads(m.weights_json),
            "stats":         json.loads(m.stats_json),
            "version":       m.version,
            "training_size": m.training_size,
        })
    except ModelWeights.DoesNotExist:
        return JsonResponse({"ok": False, "error": "No model deployed yet"})


# ═══════════════════════════════════════════════════════════════════
#  ADMIN: BATCH UPLOAD — BACKGROUND THREAD
# ═══════════════════════════════════════════════════════════════════

def _run_batch(job_id: int, files_data: list):
    """
    Background thread: OCR each image, update DB directly via psycopg2.
    This avoids Django ORM connection issues in non-request threads.
    """
    import psycopg2
    import psycopg2.extras
    import dj_database_url

    db_url  = settings.DATABASES["default"].get("NAME", "")
    db_conf = settings.DATABASES["default"]

    # Build connection kwargs from Django DB config
    conn_kwargs = {}
    if db_conf.get("ENGINE") == "django.db.backends.postgresql":
        conn_kwargs = {
            "host":     db_conf.get("HOST"),
            "port":     db_conf.get("PORT") or 5432,
            "dbname":   db_conf.get("NAME"),
            "user":     db_conf.get("USER"),
            "password": db_conf.get("PASSWORD"),
        }
        # SSL for Supabase
        conn_kwargs["sslmode"] = "require"
    else:
        # SQLite fallback — use Django ORM directly
        _run_batch_sqlite(job_id, files_data)
        return

    try:
        conn = psycopg2.connect(**conn_kwargs)
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute("UPDATE batch_jobs SET status='running' WHERE id=%s", (job_id,))
        conn.commit()

        for filename, image_bytes in files_data:
            cur.execute(
                "UPDATE batch_items SET status='processing' WHERE job_id=%s AND filename=%s",
                (job_id, filename)
            )
            conn.commit()

            try:
                text   = ocr_image_bytes(image_bytes)
                values = parse_lab_values(text)

                if len(values) >= 2:
                    cur.execute(
                        "UPDATE batch_items SET status='ready', val_count=%s, values_json=%s "
                        "WHERE job_id=%s AND filename=%s",
                        (len(values), json.dumps(values), job_id, filename)
                    )
                    cur.execute(
                        "UPDATE batch_jobs SET processed=processed+1 WHERE id=%s",
                        (job_id,)
                    )
                else:
                    cur.execute(
                        "UPDATE batch_items SET status='skipped' WHERE job_id=%s AND filename=%s",
                        (job_id, filename)
                    )
                    cur.execute(
                        "UPDATE batch_jobs SET processed=processed+1, skipped=skipped+1 WHERE id=%s",
                        (job_id,)
                    )
                conn.commit()

            except Exception as e:
                log.error(f"Batch item error [{filename}]: {e}")
                cur.execute(
                    "UPDATE batch_items SET status='failed', error=%s "
                    "WHERE job_id=%s AND filename=%s",
                    (str(e)[:200], job_id, filename)
                )
                cur.execute(
                    "UPDATE batch_jobs SET processed=processed+1, failed=failed+1 WHERE id=%s",
                    (job_id,)
                )
                conn.commit()

        cur.execute("UPDATE batch_jobs SET status='done' WHERE id=%s", (job_id,))
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        log.error(f"Batch job {job_id} fatal: {e}")
        try:
            BatchJob.objects.filter(id=job_id).update(status="error")
        except Exception:
            pass


def _run_batch_sqlite(job_id: int, files_data: list):
    """SQLite fallback for local development."""
    import sqlite3
    db_path = str(settings.DATABASES["default"]["NAME"])
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute("UPDATE batch_jobs SET status='running' WHERE id=?", (job_id,))
        conn.commit()
        for filename, image_bytes in files_data:
            conn.execute("UPDATE batch_items SET status='processing' WHERE job_id=? AND filename=?", (job_id, filename))
            conn.commit()
            try:
                text   = ocr_image_bytes(image_bytes)
                values = parse_lab_values(text)
                if len(values) >= 2:
                    conn.execute("UPDATE batch_items SET status='ready', val_count=?, values_json=? WHERE job_id=? AND filename=?",
                                 (len(values), json.dumps(values), job_id, filename))
                    conn.execute("UPDATE batch_jobs SET processed=processed+1 WHERE id=?", (job_id,))
                else:
                    conn.execute("UPDATE batch_items SET status='skipped' WHERE job_id=? AND filename=?", (job_id, filename))
                    conn.execute("UPDATE batch_jobs SET processed=processed+1, skipped=skipped+1 WHERE id=?", (job_id,))
                conn.commit()
            except Exception as e:
                conn.execute("UPDATE batch_items SET status='failed', error=? WHERE job_id=? AND filename=?", (str(e)[:200], job_id, filename))
                conn.execute("UPDATE batch_jobs SET processed=processed+1, failed=failed+1 WHERE id=?", (job_id,))
                conn.commit()
        conn.execute("UPDATE batch_jobs SET status='done' WHERE id=?", (job_id,))
        conn.commit()
    finally:
        conn.close()


@csrf_exempt
@_require_admin
def api_batch_start(request):
    """POST /api/admin/batch/start — upload images, start background OCR."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"error": "No files uploaded"}, status=400)

    files_data = [(f.name[:200], f.read()) for f in files]

    with transaction.atomic():
        job = BatchJob.objects.create(total=len(files_data))
        BatchItem.objects.bulk_create([
            BatchItem(job=job, filename=fname, status="waiting")
            for fname, _ in files_data
        ])

    threading.Thread(
        target=_run_batch,
        args=(job.id, files_data),
        daemon=True,
    ).start()

    return JsonResponse({"ok": True, "job_id": job.id, "total": len(files_data)})


def api_batch_status(request, job_id):
    """GET /api/admin/batch/<id>/status — poll progress."""
    try:
        job = BatchJob.objects.get(id=job_id)
    except BatchJob.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    items = list(job.items.values(
        "filename", "status", "val_count", "values_json", "error"
    ))
    for i in items:
        try:
            i["values"] = json.loads(i.pop("values_json") or "{}")
        except Exception:
            i["values"] = {}

    return JsonResponse({
        "job_id":    job_id,
        "total":     job.total,
        "processed": job.processed,
        "saved":     job.saved,
        "skipped":   job.skipped,
        "failed":    job.failed,
        "status":    job.status,
        "items":     items,
    })


@csrf_exempt
@_require_admin
def api_batch_approve(request, job_id, filename):
    """POST — admin approves item (with optional edits) → save to training_data."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    values = data.get("values", {})
    if not values:
        return JsonResponse({"error": "No values"}, status=400)

    clean    = {k: float(v) for k, v in values.items() if v is not None}
    features = extract_feature_vector(clean)

    with transaction.atomic():
        TrainingData.objects.create(
            source      = "admin",
            filename    = filename[:200],
            val_count   = len(clean),
            values_json = json.dumps(clean),
            features    = json.dumps(features),
        )
        BatchItem.objects.filter(job_id=job_id, filename=filename).update(status="saved")
        BatchJob.objects.filter(id=job_id).update(saved=BatchJob.objects.get(id=job_id).saved + 1)

    return JsonResponse({"ok": True})


@csrf_exempt
@_require_admin
def api_batch_skip(request, job_id, filename):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    BatchItem.objects.filter(job_id=job_id, filename=filename).update(status="skipped")
    job = BatchJob.objects.filter(id=job_id).first()
    if job:
        BatchJob.objects.filter(id=job_id).update(skipped=job.skipped + 1)
    return JsonResponse({"ok": True})


# ═══════════════════════════════════════════════════════════════════
#  ADMIN: DASHBOARD + DATA
# ═══════════════════════════════════════════════════════════════════

@_require_admin
def api_admin_stats(request):
    train_count  = TrainingData.objects.count()
    upload_count = UserUpload.objects.count()
    flagged      = UserUpload.objects.filter(flagged_cnt__gt=0).count()

    model_info = None
    try:
        m = ModelWeights.objects.get(model_id="current")
        model_info = {
            "version":       m.version,
            "training_size": m.training_size,
            "trained_at":    m.trained_at.isoformat() if m.trained_at else None,
        }
    except ModelWeights.DoesNotExist:
        pass

    recent = []
    for u in UserUpload.objects.order_by("-id")[:20]:
        recent.append({
            "filename":    u.filename,
            "val_count":   u.val_count,
            "flagged_cnt": u.flagged_cnt,
            "ml_score":    u.ml_score,
            "created_at":  u.created_at.isoformat() if u.created_at else None,
        })

    return JsonResponse({
        "train_count":    train_count,
        "upload_count":   upload_count,
        "flagged":        flagged,
        "model":          model_info,
        "recent_uploads": recent,
    })


@_require_admin
def api_admin_training(request):
    records = []
    for r in TrainingData.objects.order_by("-id")[:500]:
        records.append({
            "id":         r.id,
            "source":     r.source,
            "filename":   r.filename,
            "val_count":  r.val_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return JsonResponse({"records": records})


@csrf_exempt
@_require_admin
def api_delete_training(request, rid):
    if request.method != "DELETE":
        return JsonResponse({"error": "DELETE only"}, status=405)
    TrainingData.objects.filter(id=rid).delete()
    return JsonResponse({"ok": True})


@_require_admin
def api_admin_uploads(request):
    uploads = []
    for u in UserUpload.objects.order_by("-id")[:500]:
        uploads.append({
            "id":          u.id,
            "filename":    u.filename,
            "val_count":   u.val_count,
            "flagged_cnt": u.flagged_cnt,
            "ml_score":    u.ml_score,
            "values_json": u.values_json,
            "created_at":  u.created_at.isoformat() if u.created_at else None,
        })
    return JsonResponse({"uploads": uploads})


@csrf_exempt
@_require_admin
def api_clear_uploads(request):
    if request.method != "DELETE":
        return JsonResponse({"error": "DELETE only"}, status=405)
    UserUpload.objects.all().delete()
    return JsonResponse({"ok": True})


# ═══════════════════════════════════════════════════════════════════
#  ADMIN: MODEL TRAINING + DEPLOY
# ═══════════════════════════════════════════════════════════════════

@csrf_exempt
@_require_admin
def api_train_model(request):
    """
    POST /api/admin/model/train
    Fetches training vectors from DB, computes normalization stats,
    returns matrix to browser for TF.js training.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    if not NUMPY_AVAILABLE:
        return JsonResponse({"error": "numpy not available"}, status=503)

    try:
        data = json.loads(request.body)
    except Exception:
        data = {}

    source    = data.get("source", "both")
    min_tests = int(data.get("min_tests", 5))

    rows = []
    if source in ("admin", "both"):
        for obj in TrainingData.objects.filter(source="admin"):
            try:
                vj  = json.loads(obj.values_json)
                vec = [float(vj.get(k, 0) or 0) for k in FEATURE_KEYS]
                if sum(1 for v in vec if v > 0) >= 2:
                    rows.append(vec)
            except Exception:
                continue

    if source in ("user", "both"):
        for obj in UserUpload.objects.filter(val_count__gte=min_tests):
            try:
                vj  = json.loads(obj.values_json)
                vec = [float(vj.get(k, 0) or 0) for k in FEATURE_KEYS]
                if sum(1 for v in vec if v > 0) >= 2:
                    rows.append(vec)
            except Exception:
                continue

    if len(rows) < 5:
        return JsonResponse(
            {"error": f"Only {len(rows)} usable records. Need at least 5."},
            status=400
        )

    stats = compute_stats(rows)

    return JsonResponse({
        "ok":           True,
        "record_count": len(rows),
        "feature_keys": FEATURE_KEYS,
        "stats":        stats,
        "matrix":       rows,
    })


@csrf_exempt
@_require_admin
def api_deploy_model(request):
    """POST /api/admin/model/deploy — store trained TF.js weights in DB."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    weights = data.get("weights")
    stats   = data.get("stats")
    size    = int(data.get("training_size", 0))

    if not weights or not stats:
        return JsonResponse({"error": "Missing weights or stats"}, status=400)

    obj, created = ModelWeights.objects.get_or_create(model_id="current")
    if not created:
        obj.version += 1
    obj.weights_json  = json.dumps(weights)
    obj.stats_json    = json.dumps(stats)
    obj.training_size = size
    obj.trained_at    = timezone.now()
    obj.save()

    return JsonResponse({"ok": True, "version": obj.version})
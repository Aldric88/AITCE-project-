from app.services import cluster_resolver


class InMemoryCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find_one(self, query):
        for doc in self.docs:
            if _matches(doc, query):
                return doc
        return None

    def update_one(self, query, update, upsert=False):
        target = None
        for doc in self.docs:
            if _matches(doc, query):
                target = doc
                break

        if target is None and upsert:
            target = dict(query)
            if "$setOnInsert" in update:
                target.update(update["$setOnInsert"])
            self.docs.append(target)

        if target is None:
            return

        if "$set" in update:
            target.update(update["$set"])
        if "$inc" in update:
            for key, inc in update["$inc"].items():
                target[key] = target.get(key, 0) + inc


def _matches(doc, query):
    for key, value in query.items():
        actual = doc.get(key)
        if isinstance(value, dict):
            if "$ne" in value and actual == value["$ne"]:
                return False
            continue
        if actual != value:
            return False
    return True


def test_resolve_known_domain_by_college_type(monkeypatch):
    monkeypatch.setattr(
        cluster_resolver,
        "college_domains_collection",
        InMemoryCollection(
            [
                {
                    "domain": "psgtech.ac.in",
                    "college_id": "college_psg",
                    "is_active": True,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        cluster_resolver,
        "colleges_collection",
        InMemoryCollection(
            [
                {
                    "_id": "college_psg",
                    "name": "PSG College of Technology",
                    "university_type": "autonomous",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        cluster_resolver,
        "clusters_collection",
        InMemoryCollection(
            [
                {
                    "_id": "cluster_autonomous_default",
                    "university_type": "autonomous",
                    "is_default": True,
                }
            ]
        ),
    )

    result = cluster_resolver.resolve_user_cluster_metadata("user@psgtech.ac.in")

    assert result["verified_by_domain"] is True
    assert result["cluster_id"] == "cluster_autonomous_default"
    assert result["college_id"] == "college_psg"
    assert result["university_type"] == "autonomous"
    assert result["requires_manual_selection"] is False


def test_resolve_unknown_domain_requires_manual_selection(monkeypatch):
    monkeypatch.setattr(cluster_resolver, "college_domains_collection", InMemoryCollection())
    monkeypatch.setattr(cluster_resolver, "colleges_collection", InMemoryCollection())
    monkeypatch.setattr(cluster_resolver, "clusters_collection", InMemoryCollection())
    monkeypatch.setattr(cluster_resolver, "cluster_inference_candidates_collection", InMemoryCollection())
    monkeypatch.setattr(cluster_resolver, "_ai_classify_university_type", lambda domain: None)

    result = cluster_resolver.resolve_user_cluster_metadata("user@unknown.edu")

    assert result["verified_by_domain"] is False
    assert result["cluster_id"] is None
    assert result["requires_manual_selection"] is True


def test_resolve_unknown_domain_ai_auto_assign(monkeypatch):
    monkeypatch.setattr(cluster_resolver, "college_domains_collection", InMemoryCollection())
    monkeypatch.setattr(cluster_resolver, "colleges_collection", InMemoryCollection())
    candidates = InMemoryCollection()
    monkeypatch.setattr(cluster_resolver, "cluster_inference_candidates_collection", candidates)
    monkeypatch.setattr(
        cluster_resolver,
        "clusters_collection",
        InMemoryCollection(
            [
                {
                    "_id": "cluster_deemed_default",
                    "university_type": "deemed",
                    "is_default": True,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        cluster_resolver,
        "_ai_classify_university_type",
        lambda domain: {"university_type": "deemed", "confidence": 0.93, "reason": "domain pattern"},
    )
    monkeypatch.setenv("CLUSTER_AI_AUTO_ASSIGN_MIN_CONFIDENCE", "0.8")

    result = cluster_resolver.resolve_user_cluster_metadata("user@newcollege.example")

    assert result["verified_by_domain"] is False
    assert result["cluster_id"] == "cluster_deemed_default"
    assert result["university_type"] == "deemed"
    assert result["requires_manual_selection"] is False
    assert result["cluster_source"] == "ai_inferred"
    recorded = candidates.find_one({"domain": "newcollege.example"})
    assert recorded is not None
    assert recorded["review_status"] == "pending"
    assert recorded["last_inferred_university_type"] == "deemed"

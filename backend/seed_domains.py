from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "notes_platform")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

college_domains = db["college_domains"]
clusters = db["clusters"]
colleges = db["colleges"]

def seed():
    cluster_docs = [
        {
            "cluster_key": "anna_affiliated_default",
            "name": "Anna University Affiliated",
            "description": "Default cluster for colleges affiliated to Anna University",
            "university_type": "anna_affiliated",
            "is_default": True,
        },
        {
            "cluster_key": "autonomous_default",
            "name": "Autonomous Colleges",
            "description": "Default cluster for autonomous institutions",
            "university_type": "autonomous",
            "is_default": True,
        },
        {
            "cluster_key": "deemed_default",
            "name": "Deemed Universities",
            "description": "Default cluster for deemed universities",
            "university_type": "deemed",
            "is_default": True,
        },
    ]

    cluster_ids = {}
    for cluster in cluster_docs:
        result = clusters.update_one(
            {"cluster_key": cluster["cluster_key"]},
            {"$set": cluster},
            upsert=True,
        )
        cid = result.upserted_id or clusters.find_one({"cluster_key": cluster["cluster_key"]})["_id"]
        cluster_ids[cluster["cluster_key"]] = cid
        print(f"Cluster {cluster['cluster_key']} -> {cid}")

    college_docs = [
        {
            "name": "PSG College of Technology",
            "university_type": "autonomous",
            "cluster_key": "autonomous_default",
        },
        {
            "name": "College of Engineering, Guindy",
            "university_type": "anna_affiliated",
            "cluster_key": "anna_affiliated_default",
        },
        {
            "name": "VIT Vellore",
            "university_type": "deemed",
            "cluster_key": "deemed_default",
        },
    ]

    for college in college_docs:
        result = colleges.update_one(
            {"name": college["name"]},
            {"$set": college},
            upsert=True,
        )
        college_id = result.upserted_id or colleges.find_one({"name": college["name"]})["_id"]
        print(f"College {college['name']} -> {college_id}")

    domain_docs = [
        {
            "domain": "psgtech.ac.in",
            "college_name": "PSG College of Technology",
        },
        {
            "domain": "ceg.ac.in",
            "college_name": "College of Engineering, Guindy",
        },
        {
            "domain": "vit.ac.in",
            "college_name": "VIT Vellore",
        },
    ]

    for domain in domain_docs:
        college = colleges.find_one({"name": domain["college_name"]})
        if not college:
            continue
        cluster_key = college.get("cluster_key")
        cluster_id = cluster_ids.get(cluster_key)

        college_domains.update_one(
            {"domain": domain["domain"]},
            {
                "$set": {
                    "domain": domain["domain"],
                    "college_id": college["_id"],
                    "cluster_id": cluster_id,
                    "university_type": college.get("university_type"),
                    "is_active": True,
                }
            },
            upsert=True,
        )
        print(f"Mapped {domain['domain']} -> {college['name']} ({college.get('university_type')})")

    print(f"✅ Seeding complete for DB: {DB_NAME}")

if __name__ == "__main__":
    seed()

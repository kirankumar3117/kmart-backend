"""
Seed script: Populate the agents table with test agent codes.
Run: python seed_agents.py
"""
from app.db.session import SessionLocal
from app.models.agent import Agent

AGENTS = [
    {"name": "Ravi Kumar",   "agent_code": "AGENT007", "phone": "9999999999"},
    {"name": "Priya Sharma", "agent_code": "AGENT123", "phone": "8888888888"},
    {"name": "Test Agent",   "agent_code": "TEST001",  "phone": "7777777777"},
]

def seed():
    db = SessionLocal()
    try:
        for data in AGENTS:
            exists = db.query(Agent).filter(Agent.agent_code == data["agent_code"]).first()
            if exists:
                print(f"⏭️  Skipped (already exists): {data['agent_code']} — {data['name']}")
                continue

            agent = Agent(**data, is_active=True)
            db.add(agent)
            db.commit()
            db.refresh(agent)
            print(f"✅ Inserted: {agent.agent_code} — {agent.name} (id: {agent.id})")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
    print("\n🎉 Agent seeding complete!")

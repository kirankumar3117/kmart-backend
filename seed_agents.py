"""
Seed script: Populate the agents table and corresponding user table with test agents.
Run: python seed_agents.py
"""
from app.db.session import SessionLocal
from app.models.agent import Agent
from app.models.user import User
from app.models.shop import Shop
from app.core.security import get_password_hash

AGENTS = [
    {"name": "Ravi Kumar",   "agent_code": "AG01", "phone": "9999999991", "pin": "1234"},
    {"name": "Priya Sharma", "agent_code": "AG02", "phone": "9999999992", "pin": "1234"},
    {"name": "Test Agent",   "agent_code": "TEST", "phone": "9999999993", "pin": "1234"},
]

def seed():
    db = SessionLocal()
    try:
        # First remove existing agents to start fresh based on the prompt
        print("🧹 Cleaning up old agents...")
        
        # We need to drop the FK constraints first before we can delete the agent
        db.query(Shop).update({
            Shop.agent_id: None,
            Shop.onboarded_by_agent_id: None
        })
        db.commit()

        db.query(Agent).delete()
        db.query(User).filter(User.role == "agent").delete()
        db.commit()

        print("🌱 Seeding new agents...")
        for data in AGENTS:
            # 1. Create the Agent record in the agents table
            agent = Agent(
                name=data["name"],
                agent_code=data["agent_code"],
                phone=data["phone"],
                is_active=True
            )
            db.add(agent)

            # 2. Create the User record in the users table so they can login
            hashed_pin = get_password_hash(data["pin"])
            user = User(
                full_name=data["name"],
                phone_number=data["phone"],
                hashed_pin=hashed_pin,
                role="agent",
                is_verified=True
            )
            db.add(user)

            db.commit()
            db.refresh(agent)
            db.refresh(user)
            print(f"✅ Inserted: {agent.agent_code} — {agent.name} (Phone: {agent.phone})")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
    print("\n🎉 Agent seeding complete!")

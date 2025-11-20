"""
MongoDB Database Reset Script - Single Database
Resets all collections in the specified MongoDB database
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import re

# Database URI and name
DATABASE_URI = "mongodb+srv://omitdenimyen_db_user:omitdenimyen_db_user@cluster0.fxn6o9z.mongodb.net/smart_forwarder?appName=Cluster0"
DB_NAME = "smart_forwarder"


def mask_uri(uri: str) -> str:
    """Mask the password in the URI for logging"""
    masked = re.sub(r"://(.*?):.*?@", r"://\1:*****@", uri)
    return masked.split('?')[0]


async def reset_database():
    """Reset the database by dropping all collections"""
    try:
        print("\n" + "="*60)
        print("MongoDB Database Reset Tool")
        print("="*60)
        print(f"\nTarget Database: {DB_NAME}")
        print(f"Connection: {mask_uri(DATABASE_URI)}")
        
        # Confirm before proceeding
        print("\n⚠️  WARNING: This will DELETE ALL DATA in this database!")
        print("="*60)
        response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
        
        if response.strip().upper() != "YES":
            print("\n❌ Operation cancelled by user.")
            return
        
        print("\n🔄 Starting database reset...\n")
        print("="*60)
        
        # Connect to database
        client = AsyncIOMotorClient(DATABASE_URI)
        db = client[DB_NAME]
        
        # Get all collection names
        collections = await db.list_collection_names()
        
        if not collections:
            print(f"✓ Database is already empty (no collections found)")
            client.close()
            print("\n✅ Nothing to reset!")
            return
        
        print(f"\nFound {len(collections)} collection(s):")
        for col in collections:
            # Get document count for each collection
            count = await db[col].count_documents({})
            print(f"  - {col} ({count} documents)")
        
        # Drop each collection
        print(f"\nDropping collections...")
        for collection_name in collections:
            await db[collection_name].drop()
            print(f"  ✓ Dropped: {collection_name}")
        
        # Verify all collections are dropped
        remaining = await db.list_collection_names()
        if not remaining:
            print(f"\n✅ Database reset successfully!")
        else:
            print(f"\n⚠️  Warning: Some collections still exist: {remaining}")
        
        client.close()
        
        print("\n" + "="*60)
        print("✅ Database has been completely reset!")
        print("="*60)
        print("\nThe database is now empty and ready for fresh data.")
        print()
        
    except Exception as e:
        print(f"\n❌ Error resetting database: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(reset_database())
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        exit(1)

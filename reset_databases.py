"""
MongoDB Database Reset Script
Resets all collections in the specified MongoDB databases
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import re

# Database URIs
DATABASE_URIS = [
    "mongodb+srv://knollguruunsworn_db_user:knollguruunsworn_db_user@cluster0.ncf3tpp.mongodb.net/?appName=Cluster0",
    "mongodb+srv://plentydabbuffalo_db_user:plentydabbuffalo_db_user@cluster0.vayaynb.mongodb.net/?appName=Cluster0"
]

DB_NAME = "dbFyvio"


def mask_uri(uri: str) -> str:
    """Mask the password in the URI for logging"""
    masked = re.sub(r"://(.*?):.*?@", r"://\1:*****@", uri)
    return masked.split('?')[0]


async def reset_database(uri: str, db_name: str, db_index: int):
    """Reset a single database by dropping all collections"""
    try:
        print(f"\n{'='*60}")
        print(f"Processing Database {db_index + 1}: {mask_uri(uri)}")
        print(f"{'='*60}")
        
        # Connect to database
        client = AsyncIOMotorClient(uri)
        db = client[db_name]
        
        # Get all collection names
        collections = await db.list_collection_names()
        
        if not collections:
            print(f"✓ Database is already empty (no collections found)")
            client.close()
            return
        
        print(f"\nFound {len(collections)} collection(s):")
        for col in collections:
            print(f"  - {col}")
        
        # Drop each collection
        print(f"\nDropping collections...")
        for collection_name in collections:
            await db[collection_name].drop()
            print(f"  ✓ Dropped: {collection_name}")
        
        # Verify all collections are dropped
        remaining = await db.list_collection_names()
        if not remaining:
            print(f"\n✅ Database {db_index + 1} reset successfully!")
        else:
            print(f"\n⚠️  Warning: Some collections still exist: {remaining}")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error resetting database {db_index + 1}: {e}")
        raise


async def main():
    """Main function to reset all databases"""
    print("\n" + "="*60)
    print("MongoDB Database Reset Tool")
    print("="*60)
    print(f"\nTarget Database Name: {DB_NAME}")
    print(f"Number of Databases: {len(DATABASE_URIS)}")
    
    # Confirm before proceeding
    print("\n⚠️  WARNING: This will DELETE ALL DATA in the following databases:")
    for i, uri in enumerate(DATABASE_URIS):
        db_type = "Tracking DB" if i == 0 else f"Storage DB {i}"
        print(f"  {i + 1}. {db_type}: {mask_uri(uri)}")
    
    print("\n" + "="*60)
    response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
    
    if response.strip().upper() != "YES":
        print("\n❌ Operation cancelled by user.")
        return
    
    print("\n🔄 Starting database reset...\n")
    
    # Reset each database
    for index, uri in enumerate(DATABASE_URIS):
        await reset_database(uri, DB_NAME, index)
    
    print("\n" + "="*60)
    print("✅ All databases have been reset successfully!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Restart your application")
    print("  2. Use /scan command to re-index your Telegram channels")
    print("  3. Or forward new files to AUTH_CHANNEL to start fresh")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user (Ctrl+C)")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        exit(1)

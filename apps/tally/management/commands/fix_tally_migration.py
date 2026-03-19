from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Manually add updated_by and updated_at fields to TallyInfo if migration failed'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tally_tallyinfo' 
                AND column_name IN ('updated_at', 'updated_by_id')
            """)
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            if 'updated_at' in existing_columns and 'updated_by_id' in existing_columns:
                self.stdout.write(self.style.SUCCESS('✓ Columns already exist'))
                return
            
            # Add updated_at if missing
            if 'updated_at' not in existing_columns:
                self.stdout.write('Adding updated_at column...')
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo 
                    ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                """)
                self.stdout.write(self.style.SUCCESS('✓ Added updated_at'))
            
            # Add updated_by_id if missing
            if 'updated_by_id' not in existing_columns:
                self.stdout.write('Adding updated_by_id column...')
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo 
                    ADD COLUMN updated_by_id INTEGER NULL
                """)
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo 
                    ADD CONSTRAINT tally_tallyinfo_updated_by_id_fkey 
                    FOREIGN KEY (updated_by_id) 
                    REFERENCES accounts_account(id) 
                    ON DELETE SET NULL
                """)
                cursor.execute("""
                    CREATE INDEX tally_tallyinfo_updated_by_id_idx 
                    ON tally_tallyinfo(updated_by_id)
                """)
                self.stdout.write(self.style.SUCCESS('✓ Added updated_by_id'))
            
            self.stdout.write(self.style.SUCCESS('✓ Migration fix completed'))

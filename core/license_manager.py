"""
License Manager with Remote Kill Switch
Provides full control over license activation and revocation
"""
import hashlib
import uuid
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Tuple

import config


class LicenseStatus:
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    INVALID = "INVALID"


class LicenseManager:
    """
    License management with remote validation and kill switch capability.
    
    How it works:
    1. On startup, check if a license key exists locally
    2. If no key -> TRIAL mode (limited to 30 entries)
    3. If key exists -> Validate against remote server
    4. Server returns: VALID, REVOKED, or INVALID
    5. If REVOKED or INVALID -> Block app immediately (Kill Switch)
    6. If offline -> Use cached validation with grace period
    7. Grace period expired -> Block until online validation succeeds
    """
    
    def __init__(self, db):
        self.db = db
        self._cached_status = None
        self._machine_id = self._get_machine_id()
    
    def _get_machine_id(self) -> str:
        """Generate unique machine identifier"""
        try:
            # Combine multiple hardware identifiers
            import platform
            import getpass
            
            components = [
                platform.node(),
                platform.machine(),
                platform.processor()[:50] if platform.processor() else '',
                getpass.getuser(),
            ]
            
            # Try to get MAC address
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 48, 8)][::-1])
                components.append(mac)
            except:
                pass
            
            # Create hash
            combined = '|'.join(components)
            return hashlib.sha256(combined.encode()).hexdigest()[:32]
        except:
            # Fallback to random UUID (stored persistently)
            return str(uuid.uuid4()).replace('-', '')[:32]
    
    def get_current_status(self) -> Tuple[str, dict]:
        """
        Get current license status with details.
        Returns: (status, details_dict)
        """
        license_info = self._get_stored_license()
        
        if not license_info or not license_info.get('license_key'):
            return LicenseStatus.TRIAL, {
                'message': 'Trial Mode - Limited to 30 entries',
                'entries_used': self.db.get_entry_count(),
                'entries_limit': config.TRIAL_ENTRY_LIMIT,
                'machine_id': self._machine_id
            }
        
        # Check cached validation first
        if self._is_cache_valid(license_info):
            cached_result = license_info.get('last_validation_result', 'UNKNOWN')
            if cached_result == 'VALID':
                return LicenseStatus.ACTIVE, {
                    'message': 'License Active',
                    'license_key': self._mask_key(license_info['license_key']),
                    'activated_on': license_info.get('activation_date', 'Unknown'),
                    'last_validated': license_info.get('last_validated', 'Never')
                }
        
        # Attempt remote validation
        result = self._validate_remote(license_info['license_key'])
        
        if result['status'] == 'VALID':
            self._update_validation_cache(license_info['license_key'], 'VALID')
            return LicenseStatus.ACTIVE, {
                'message': 'License Active',
                'license_key': self._mask_key(license_info['license_key'])
            }
        
        elif result['status'] == 'REVOKED':
            self._update_validation_cache(license_info['license_key'], 'REVOKED')
            return LicenseStatus.REVOKED, {
                'message': '⚠️ LICENSE REVOKED - Please contact support',
                'reason': result.get('reason', 'License has been revoked by administrator')
            }
        
        elif result['status'] == 'INVALID':
            return LicenseStatus.INVALID, {
                'message': '❌ Invalid license key',
                'reason': 'This key is not recognized'
            }
        
        elif result['status'] == 'OFFLINE':
            # Check grace period
            if self._is_grace_period_valid(license_info):
                return LicenseStatus.ACTIVE, {
                    'message': 'License Active (Offline Mode)',
                    'license_key': self._mask_key(license_info['license_key']),
                    'warning': 'Please connect to internet to validate license'
                }
            else:
                return LicenseStatus.EXPIRED, {
                    'message': '⚠️ License validation required',
                    'reason': 'Please connect to internet to validate your license'
                }
        
        return LicenseStatus.INVALID, {'message': 'Unknown license status'}
    
    def _validate_remote(self, license_key: str) -> dict:
        """Validate license key against remote server"""
        try:
            response = requests.get(config.LICENSE_SERVER_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                valid_keys = data.get('valid_keys', [])
                revoked_keys = data.get('revoked_keys', [])
                
                # Check if machine-bound key
                # Keys can be plain or in format: KEY:MACHINE_ID
                key_with_machine = f"{license_key}:{self._machine_id}"
                
                if license_key in revoked_keys or key_with_machine in revoked_keys:
                    return {'status': 'REVOKED', 'reason': 'License revoked by administrator'}
                
                if license_key in valid_keys or key_with_machine in valid_keys:
                    return {'status': 'VALID'}
                
                # Check if key exists but for different machine
                for vk in valid_keys:
                    if vk.startswith(license_key + ':') and vk != key_with_machine:
                        return {'status': 'INVALID', 'reason': 'This key is registered to a different machine'}
                
                return {'status': 'INVALID'}
            
            return {'status': 'OFFLINE', 'reason': 'Server unreachable'}
            
        except requests.exceptions.RequestException:
            return {'status': 'OFFLINE', 'reason': 'No internet connection'}
        except Exception as e:
            return {'status': 'OFFLINE', 'reason': str(e)}
    
    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """
        Activate a new license key.
        Returns: (success, message)
        """
        license_key = license_key.strip().upper()
        
        # Basic format validation
        if not self._validate_key_format(license_key):
            return False, "Invalid key format. Expected: XXXX-XXXX-XXXX-XXXX"
        
        # Remote validation
        result = self._validate_remote(license_key)
        
        if result['status'] == 'VALID':
            # Store license
            self._store_license(license_key)
            return True, "✅ License activated successfully!"
        
        elif result['status'] == 'REVOKED':
            return False, "❌ This license has been revoked. Please contact support."
        
        elif result['status'] == 'INVALID':
            return False, f"❌ Invalid license key. {result.get('reason', '')}"
        
        else:  # OFFLINE
            return False, "⚠️ Cannot validate license. Please check your internet connection."
    
    def _validate_key_format(self, key: str) -> bool:
        """Validate license key format"""
        # Expected format: XXXX-XXXX-XXXX-XXXX (16 chars + 3 dashes)
        parts = key.split('-')
        if len(parts) != 4:
            return False
        return all(len(p) == 4 and p.isalnum() for p in parts)
    
    def _store_license(self, license_key: str):
        """Store license in database"""
        now = datetime.now().isoformat()
        self.db.execute("""
            INSERT OR REPLACE INTO license (id, license_key, machine_id, status, activation_date, last_validated, last_validation_result)
            VALUES (1, ?, ?, 'ACTIVE', ?, ?, 'VALID')
        """, (license_key, self._machine_id, now, now))
    
    def _get_stored_license(self) -> Optional[dict]:
        """Get stored license from database"""
        result = self.db.execute("SELECT * FROM license WHERE id = 1")
        if result:
            row = result[0]
            return {
                'license_key': row['license_key'],
                'machine_id': row['machine_id'],
                'status': row['status'],
                'activation_date': row['activation_date'],
                'last_validated': row['last_validated'],
                'last_validation_result': row['last_validation_result']
            }
        return None
    
    def _update_validation_cache(self, license_key: str, result: str):
        """Update cached validation result"""
        now = datetime.now().isoformat()
        self.db.execute("""
            UPDATE license SET last_validated = ?, last_validation_result = ? WHERE id = 1
        """, (now, result))
    
    def _is_cache_valid(self, license_info: dict) -> bool:
        """Check if cached validation is still valid"""
        last_validated = license_info.get('last_validated')
        if not last_validated:
            return False
        
        try:
            last_dt = datetime.fromisoformat(last_validated)
            cache_expiry = timedelta(hours=config.LICENSE_CHECK_INTERVAL_HOURS)
            return datetime.now() - last_dt < cache_expiry
        except:
            return False
    
    def _is_grace_period_valid(self, license_info: dict) -> bool:
        """Check if offline grace period is still valid"""
        last_validated = license_info.get('last_validated')
        last_result = license_info.get('last_validation_result')
        
        if not last_validated or last_result != 'VALID':
            return False
        
        try:
            last_dt = datetime.fromisoformat(last_validated)
            grace_period = timedelta(days=config.GRACE_PERIOD_DAYS)
            return datetime.now() - last_dt < grace_period
        except:
            return False
    
    def _mask_key(self, key: str) -> str:
        """Mask license key for display"""
        if len(key) >= 8:
            return key[:4] + '-****-****-' + key[-4:]
        return '****'
    
    def can_create_entry(self) -> Tuple[bool, str]:
        """Check if user can create a new entry based on license"""
        status, details = self.get_current_status()
        
        if status == LicenseStatus.REVOKED:
            return False, "License revoked. Application is locked."
        
        if status == LicenseStatus.EXPIRED:
            return False, "License expired. Please validate your license."
        
        if status == LicenseStatus.INVALID:
            return False, "Invalid license. Please enter a valid license key."
        
        if status == LicenseStatus.TRIAL:
            entries_used = self.db.get_entry_count()
            if entries_used >= config.TRIAL_ENTRY_LIMIT:
                return False, f"Trial limit reached ({config.TRIAL_ENTRY_LIMIT} entries). Please purchase a license."
            return True, f"Trial: {entries_used}/{config.TRIAL_ENTRY_LIMIT} entries used"
        
        # ACTIVE
        return True, "License active"
    
    def is_app_blocked(self) -> Tuple[bool, str]:
        """Check if the entire app should be blocked"""
        status, details = self.get_current_status()
        
        if status == LicenseStatus.REVOKED:
            return True, details.get('message', 'License revoked')
        
        if status == LicenseStatus.EXPIRED:
            return True, details.get('message', 'License expired')
        
        return False, ""
    
    def get_machine_id(self) -> str:
        """Get machine ID for display"""
        return self._machine_id


# ============================================================================
# LICENSE KEY GENERATOR - FOR ADMIN USE ONLY
# ============================================================================
# This section should be kept separate and secure. 
# Do NOT distribute this with the client application.

class LicenseKeyGenerator:
    """
    Admin tool forward generation license keys.
    Keep this file secure - do not distribute with client app!
    """
    
    SECRET_SALT = "AccuBooks2024SecretSalt!@#$"  # Change this to your own secret
    
    @classmethod
    def generate_key(cls, prefix: str = "ACCT") -> str:
        """Generate a new random license key"""
        import secrets
        import string
        
        chars = string.ascii_uppercase + string.digits
        parts = [
            prefix,
            ''.join(secrets.choice(chars) for _ in range(4)),
            ''.join(secrets.choice(chars) for _ in range(4)),
            ''.join(secrets.choice(chars) for _ in range(4))
        ]
        return '-'.join(parts)
    
    @classmethod
    def generate_batch(cls, count: int, prefix: str = "ACCT") -> list:
        """Generate multiple unique keys"""
        keys = set()
        while len(keys) < count:
            keys.add(cls.generate_key(prefix))
        return list(keys)
    
    @classmethod
    def create_license_server_json(cls, valid_keys: list, revoked_keys: list = None) -> str:
        """Create JSON content for license server"""
        data = {
            "valid_keys": valid_keys,
            "revoked_keys": revoked_keys or [],
            "updated_at": datetime.now().isoformat()
        }
        return json.dumps(data, indent=2)


if __name__ == "__main__":
    # Admin key generation script
    print("=" * 50)
    print("LICENSE KEY GENERATOR - ADMIN TOOL")
    print("=" * 50)
    
    # Generate some sample keys
    keys = LicenseKeyGenerator.generate_batch(5)
    print("\nGenerated License Keys:")
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {key}")
    
    # Create sample license server JSON
    print("\n\nSample license server JSON (host on GitHub Gist):")
    print("-" * 50)
    print(LicenseKeyGenerator.create_license_server_json(keys))
    print("-" * 50)
    print("\n1. Create a secret GitHub Gist with above JSON")
    print("2. Get the RAW URL of the Gist")
    print("3. Update LICENSE_SERVER_URL in config.py")
    print("4. To revoke a key, move it from valid_keys to revoked_keys")
